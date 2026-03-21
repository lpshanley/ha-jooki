"""Switch platform for the Jooki integration."""

from __future__ import annotations

import json
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JookiConfigEntry
from .const import DOMAIN, SIGNAL_STATE_UPDATED
from .mqtt_client import JookiMqttClient


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JookiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jooki switches from a config entry."""
    async_add_entities([JookiToySafeSwitch(entry.runtime_data, entry)])


class JookiToySafeSwitch(SwitchEntity):
    """Switch to toggle Toy Safe content filtering mode."""

    _attr_has_entity_name = True
    _attr_name = "Toy Safe"
    _attr_icon = "mdi:shield-baby"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, client: JookiMqttClient, entry: JookiConfigEntry) -> None:
        """Initialize the Toy Safe switch."""
        self._client = client
        self._cfg = client.device_config
        self._attr_unique_id = f"{entry.entry_id}_toy_safe"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
        )
        self._signal = SIGNAL_STATE_UPDATED.format(entry.entry_id)

    async def async_added_to_hass(self) -> None:
        """Subscribe to state updates."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._signal, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        """Handle a state update from the MQTT client."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if the device is available."""
        return self._client.state.available

    @property
    def is_on(self) -> bool:
        """Return True if Toy Safe mode is enabled."""
        return self._client.state.device.toy_safe

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable Toy Safe mode."""
        await self._client.async_publish(
            self._cfg.topic_set_toy_safe, json.dumps({"enable": True})
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable Toy Safe mode."""
        await self._client.async_publish(
            self._cfg.topic_set_toy_safe, json.dumps({"enable": False})
        )
