"""The Jooki integration."""

from __future__ import annotations

from typing import cast

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    CONF_DEVICE_VERSION,
    DEVICE_VERSION_V1,
    DOMAIN,
    PLATFORMS,
    SIGNAL_STATE_UPDATED,
)
from .device_commands import JookiDevice
from .device_config import get_device_config
from .identity import normalize_device_identity
from .mqtt_client import JookiMqttClient

type JookiConfigEntry = ConfigEntry[JookiDevice]

SERVICE_SKIP_SECONDS = "skip_seconds"
SERVICE_SKIP_SECONDS_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("delta_s"): vol.Coerce(int),
    }
)
SERVICE_DISMISS_MESSAGE = "dismiss_message"
SERVICE_DISMISS_MESSAGE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("message_id"): vol.Coerce(int),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: JookiConfigEntry) -> bool:
    """Set up Jooki from a config entry."""
    version = entry.data.get(CONF_DEVICE_VERSION, DEVICE_VERSION_V1)
    device_config = get_device_config(version)

    client = JookiMqttClient(
        hass,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        entry_id=entry.entry_id,
        device_config=device_config,
    )
    entry.runtime_data = client
    _watch_device_identity(hass, entry)
    await client.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _register_services(hass)
    return True


def _watch_device_identity(hass: HomeAssistant, entry: JookiConfigEntry) -> None:
    """Set the config entry unique id from the first valid device id.

    Empty connect state and slices without a Jooki id are ignored. The
    listener is removed once an id normalizes, so a later slice that clears
    device.id leaves the unique id in place. The update does not reload.
    """
    signal = SIGNAL_STATE_UPDATED.format(entry.entry_id)
    removed = False

    def _remove() -> None:
        nonlocal removed
        if removed:
            return
        removed = True
        remove_listener()

    def _on_state() -> None:
        device = entry.runtime_data.state.device
        hostname = normalize_device_identity(device.device_id, device.hostname)
        if hostname is None:
            return
        _remove()
        if entry.unique_id == hostname:
            return
        owner = hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, hostname)
        if owner is not None and owner.entry_id != entry.entry_id:
            return
        hass.config_entries.async_update_entry(entry, unique_id=hostname)

    remove_listener = async_dispatcher_connect(hass, signal, _on_state)
    entry.async_on_unload(_remove)


def _client_for_device(hass: HomeAssistant, device_id: str) -> JookiDevice:
    """Return the Jooki client for a Home Assistant device id."""
    device_reg = dr.async_get(hass)
    device = device_reg.async_get(device_id)
    if not device:
        raise ServiceValidationError(
            f"Device {device_id} not found",
            translation_key="device_not_found",
        )

    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry and entry.domain == DOMAIN:
            return entry.runtime_data

    raise ServiceValidationError(
        f"No Jooki config entry found for device {device_id}",
        translation_key="not_jooki_device",
    )


def _register_services(hass: HomeAssistant) -> None:
    """Register integration-level services (idempotent)."""

    async def handle_skip_seconds(call: ServiceCall) -> None:
        """Handle the skip_seconds service call."""
        client = _client_for_device(hass, call.data["device_id"])
        await client.async_skip_seconds(call.data["delta_s"])

    async def handle_dismiss_message(call: ServiceCall) -> None:
        """Handle the dismiss_message service call."""
        client = _client_for_device(hass, call.data["device_id"])
        await client.async_dismiss_message(call.data["message_id"])

    if not hass.services.has_service(DOMAIN, SERVICE_SKIP_SECONDS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SKIP_SECONDS,
            handle_skip_seconds,
            schema=SERVICE_SKIP_SECONDS_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_DISMISS_MESSAGE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_DISMISS_MESSAGE,
            handle_dismiss_message,
            schema=SERVICE_DISMISS_MESSAGE_SCHEMA,
        )


async def async_unload_entry(hass: HomeAssistant, entry: JookiConfigEntry) -> bool:
    """Unload a Jooki config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await cast(JookiMqttClient, entry.runtime_data).async_stop()
    return unload_ok
