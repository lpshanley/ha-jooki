"""Light platform for the Jooki integration (LED ring control)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JookiConfigEntry
from .const import DOMAIN, SIGNAL_STATE_UPDATED
from .mqtt_client import JookiMqttClient

# Effect definitions: name → (topic_attr, payload)
EFFECT_PULSE_RED = "Pulse Red"
EFFECT_PULSE_GREEN = "Pulse Green"
EFFECT_PULSE_BLUE = "Pulse Blue"
EFFECT_PULSE_WHITE = "Pulse White"
EFFECT_CHARGE_INC = "Charge Animation (Increasing)"
EFFECT_CHARGE_DEC = "Charge Animation (Decreasing)"

PULSE_EFFECTS: dict[str, str] = {
    EFFECT_PULSE_RED: "ALL,255,0,0,3,500,1.0",
    EFFECT_PULSE_GREEN: "ALL,0,200,0,3,500,1.0",
    EFFECT_PULSE_BLUE: "ALL,0,10,200,3,500,1.0",
    EFFECT_PULSE_WHITE: "ALL,200,200,200,3,500,1.0",
}

CHARGE_EFFECTS: dict[str, str] = {
    EFFECT_CHARGE_INC: "BAT_INC",
    EFFECT_CHARGE_DEC: "BAT_DEC",
}

ALL_EFFECTS = list(PULSE_EFFECTS) + list(CHARGE_EFFECTS)


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
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = ALL_EFFECTS

    def __init__(self, client: JookiMqttClient, entry: JookiConfigEntry) -> None:
        """Initialize the LED ring light."""
        self._client = client
        self._cfg = client.device_config
        self._attr_unique_id = f"{entry.entry_id}_led_ring"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
        )
        self._signal = SIGNAL_STATE_UPDATED.format(entry.entry_id)
        self._is_on = False
        self._rgb_color: tuple[int, int, int] = (255, 255, 255)
        self._attr_effect: str | None = None

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
        """Turn on the LED ring with optional color or effect."""
        effect = kwargs.get(ATTR_EFFECT)

        if effect:
            await self._apply_effect(effect)
            self._attr_effect = effect
            self._is_on = True
            self.async_write_ha_state()
            return

        if ATTR_RGB_COLOR in kwargs:
            self._rgb_color = tuple(int(c) for c in kwargs[ATTR_RGB_COLOR])

        # Clear any active effect when setting a static color
        self._attr_effect = None
        r, g, b = self._rgb_color
        await self._client.async_publish(self._cfg.topic_led_set_raw, f"ALL,{r},{g},{b}")
        self._is_on = True
        self.async_write_ha_state()

    async def _apply_effect(self, effect: str) -> None:
        """Apply a pulse or charge animation effect."""
        if effect in PULSE_EFFECTS:
            await self._client.async_publish(
                self._cfg.topic_led_pulse_raw, PULSE_EFFECTS[effect]
            )
        elif effect in CHARGE_EFFECTS:
            await self._client.async_publish(
                self._cfg.topic_led_charge_state, CHARGE_EFFECTS[effect]
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the LED ring."""
        await self._client.async_publish(self._cfg.topic_led_set_raw, "ALL,0,0,0")
        self._is_on = False
        self._attr_effect = None
        self.async_write_ha_state()
