"""Light platform for the Jooki integration (LED ring control)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JookiConfigEntry
from .const import DOMAIN, SIGNAL_STATE_UPDATED, TOPIC_LED_SET_RAW
from .mqtt_client import JookiMqttClient


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JookiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jooki LED light from a config entry."""
    async_add_entities([JookiLedLight(entry.runtime_data, entry)])


class JookiLedLight(LightEntity):
    """Representation of the Jooki LED ring."""

    _attr_has_entity_name = True
    _attr_name = "LED Ring"
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB

    def __init__(self, client: JookiMqttClient, entry: JookiConfigEntry) -> None:
        """Initialize the LED ring light."""
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_led_ring"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
        )
        self._signal = SIGNAL_STATE_UPDATED.format(entry.entry_id)
        self._is_on = False
        self._rgb_color: tuple[int, int, int] = (255, 255, 255)

    async def async_added_to_hass(self) -> None:
        """Subscribe to state updates (for availability tracking)."""
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
        """Return True if the LED ring is on."""
        return self._is_on

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the current RGB color."""
        return self._rgb_color

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the LED ring."""
        if "rgb_color" in kwargs:
            self._rgb_color = tuple(int(c) for c in kwargs["rgb_color"])
        r, g, b = self._rgb_color
        await self._client.async_publish(TOPIC_LED_SET_RAW, f"ALL,{r},{g},{b}")
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the LED ring."""
        await self._client.async_publish(TOPIC_LED_SET_RAW, "ALL,0,0,0")
        self._is_on = False
        self.async_write_ha_state()
