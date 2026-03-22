"""Event platform for the Jooki integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JookiConfigEntry
from .const import DOMAIN, SIGNAL_BUTTON_EVENT, SIGNAL_NFC_EVENT, SIGNAL_VOLUME_EVENT
from .mqtt_client import JookiMqttClient


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JookiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jooki event entities from a config entry."""
    client = entry.runtime_data
    async_add_entities([
        JookiNfcEvent(client, entry),
        JookiButtonEvent(client, entry, "next", "Next Button"),
        JookiButtonEvent(client, entry, "previous", "Previous Button"),
        JookiButtonEvent(client, entry, "circle", "Circle Button"),
        JookiVolumeKnobEvent(client, entry),
    ])


class JookiNfcEvent(EventEntity):
    """Event entity for NFC figurine placement/removal."""

    _attr_has_entity_name = True
    _attr_name = "Figurine"
    _attr_icon = "mdi:teddy-bear"
    _attr_event_types = ["figurine_placed", "figurine_removed"]

    def __init__(self, client: JookiMqttClient, entry: JookiConfigEntry) -> None:
        """Initialize the NFC event entity."""
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_nfc_event"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
        )
        self._signal = SIGNAL_NFC_EVENT.format(entry.entry_id)

    async def async_added_to_hass(self) -> None:
        """Subscribe to NFC event signals."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self._signal, self._handle_nfc_event
            )
        )

    @callback
    def _handle_nfc_event(
        self, event_type: str, event_data: dict[str, Any]
    ) -> None:
        """Handle an NFC event from the MQTT client."""
        self._trigger_event(event_type, event_data)
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if the device is available."""
        return self._client.state.available


class JookiButtonEvent(EventEntity):
    """Event entity for a physical button press/release."""

    _attr_has_entity_name = True
    _attr_event_types = ["pressed", "released"]

    def __init__(
        self,
        client: JookiMqttClient,
        entry: JookiConfigEntry,
        button_key: str,
        name: str,
    ) -> None:
        """Initialize the button event entity."""
        self._client = client
        self._button_key = button_key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_button_{button_key}"
        self._attr_icon = "mdi:gesture-tap-button"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
        )
        self._signal = SIGNAL_BUTTON_EVENT.format(entry.entry_id)

    async def async_added_to_hass(self) -> None:
        """Subscribe to button event signals."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self._signal, self._handle_button_event
            )
        )

    @callback
    def _handle_button_event(self, button_name: str, event_type: str) -> None:
        """Handle a button event from the MQTT client."""
        if button_name == self._button_key:
            self._trigger_event(event_type, {"button": button_name})
            self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if the device is available."""
        return self._client.state.available


class JookiVolumeKnobEvent(EventEntity):
    """Event entity for the physical volume knob."""

    _attr_has_entity_name = True
    _attr_name = "Volume Knob"
    _attr_icon = "mdi:knob"
    _attr_event_types = ["volume_changed"]

    def __init__(self, client: JookiMqttClient, entry: JookiConfigEntry) -> None:
        """Initialize the volume knob event entity."""
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_volume_knob"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
        )
        self._signal = SIGNAL_VOLUME_EVENT.format(entry.entry_id)

    async def async_added_to_hass(self) -> None:
        """Subscribe to volume knob event signals."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self._signal, self._handle_volume_event
            )
        )

    @callback
    def _handle_volume_event(self, vol: str) -> None:
        """Handle a volume knob event from the MQTT client."""
        self._trigger_event("volume_changed", {"volume": vol})
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if the device is available."""
        return self._client.state.available
