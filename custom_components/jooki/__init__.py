"""The Jooki integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_VERSION, DEVICE_VERSION_V1, DOMAIN, PLATFORMS, get_device_config
from .mqtt_client import JookiMqttClient

type JookiConfigEntry = ConfigEntry[JookiMqttClient]


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
    return True


async def async_unload_entry(hass: HomeAssistant, entry: JookiConfigEntry) -> bool:
    """Unload a Jooki config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_stop()
    return unload_ok
