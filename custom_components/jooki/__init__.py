"""The Jooki integration."""

from __future__ import annotations

import json
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr

from .const import CONF_DEVICE_VERSION, DEVICE_VERSION_V1, DOMAIN, PLATFORMS, get_device_config
from .mqtt_client import JookiMqttClient

_LOGGER = logging.getLogger(__name__)

type JookiConfigEntry = ConfigEntry[JookiMqttClient]

SERVICE_CREATE_PLAYLIST = "create_playlist"
SERVICE_RENAME_FIGURINE = "rename_figurine"


def _get_client_for_device(
    hass: HomeAssistant, device_id: str
) -> JookiMqttClient:
    """Resolve a device_id to a JookiMqttClient.

    Raises HomeAssistantError if the device cannot be found.
    """
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(device_id)
    if not device:
        raise HomeAssistantError(f"Jooki device '{device_id}' not found")

    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry and entry.domain == DOMAIN and hasattr(entry, "runtime_data"):
            return entry.runtime_data

    raise HomeAssistantError(f"No Jooki integration entry found for device '{device_id}'")


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
    await client.async_start()

    entry.runtime_data = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services (only once across all entries)
    if not hass.services.has_service(DOMAIN, SERVICE_CREATE_PLAYLIST):
        _register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: JookiConfigEntry) -> bool:
    """Unload a Jooki config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_stop()

    # Remove services if no more entries
    entries = hass.config_entries.async_entries(DOMAIN)
    remaining = [e for e in entries if e.entry_id != entry.entry_id]
    if not remaining:
        hass.services.async_remove(DOMAIN, SERVICE_CREATE_PLAYLIST)
        hass.services.async_remove(DOMAIN, SERVICE_RENAME_FIGURINE)

    return unload_ok


def _register_services(hass: HomeAssistant) -> None:
    """Register Jooki custom services."""

    async def handle_create_playlist(call: ServiceCall) -> None:
        """Handle the create_playlist service call."""
        client = _get_client_for_device(hass, call.data["device_id"])
        payload = {
            "title": call.data.get("title"),
            "audiobook": call.data.get("audiobook", False),
        }
        await client.async_publish(
            client.device_config.topic_playlist_new,
            json.dumps(payload),
        )

    async def handle_rename_figurine(call: ServiceCall) -> None:
        """Handle the rename_figurine service call."""
        client = _get_client_for_device(hass, call.data["device_id"])
        payload = {
            "tagId": call.data["tag_id"],
            "name": call.data["name"],
        }
        await client.async_publish(
            client.device_config.topic_token_edit,
            json.dumps(payload),
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_PLAYLIST,
        handle_create_playlist,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RENAME_FIGURINE,
        handle_rename_figurine,
    )
