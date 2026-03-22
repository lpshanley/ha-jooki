"""The Jooki integration."""

from __future__ import annotations

import json

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import CONF_DEVICE_VERSION, DEVICE_VERSION_V1, DOMAIN, PLATFORMS, get_device_config
from .mqtt_client import JookiMqttClient

type JookiConfigEntry = ConfigEntry[JookiMqttClient]

SERVICE_SKIP_SECONDS = "skip_seconds"
SERVICE_SKIP_SECONDS_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("delta_s"): vol.Coerce(int),
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
    await client.async_start()

    entry.runtime_data = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _register_services(hass)
    return True


def _register_services(hass: HomeAssistant) -> None:
    """Register integration-level services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_SKIP_SECONDS):
        return

    async def handle_skip_seconds(call: ServiceCall) -> None:
        """Handle jooki.skip_seconds service call."""
        device_id = call.data["device_id"]
        delta_s = call.data["delta_s"]

        device_reg = dr.async_get(hass)
        device = device_reg.async_get(device_id)
        if not device:
            raise ServiceValidationError(
                f"Device {device_id} not found",
                translation_key="device_not_found",
            )

        # Find the config entry for this device
        for entry_id in device.config_entries:
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry and entry.domain == DOMAIN:
                client: JookiMqttClient = entry.runtime_data
                await client.async_publish(
                    client.device_config.topic_skip_sec,
                    json.dumps({"delta_s": delta_s}),
                )
                return

        raise ServiceValidationError(
            f"No Jooki config entry found for device {device_id}",
            translation_key="not_jooki_device",
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SKIP_SECONDS,
        handle_skip_seconds,
        schema=SERVICE_SKIP_SECONDS_SCHEMA,
    )


async def async_unload_entry(hass: HomeAssistant, entry: JookiConfigEntry) -> bool:
    """Unload a Jooki config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_stop()
    return unload_ok
