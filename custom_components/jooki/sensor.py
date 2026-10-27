"""Sensor platform for the Jooki integration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JookiConfigEntry
from .const import DOMAIN, SIGNAL_STATE_UPDATED
from .device_commands import JookiDevice
from .models import JookiState, figurine_label


def _disk_usage_percent(state: JookiState) -> int | None:
    """Extract disk usage percentage from device state."""
    du = state.device.disk_usage
    if du and isinstance(du, dict):
        return du.get("usedPercent")
    return None


def _playback_source(state: JookiState) -> str | None:
    """Return the current playback service (SPOTIFY, FILE, STREAM, etc.)."""
    return state.now_playing.service


def _current_playlist(state: JookiState) -> str | None:
    """Resolve the current playlist ID to its title."""
    pid = state.now_playing.playlist_id
    if not pid:
        return None
    playlist = state.db.playlists.get(pid)
    return playlist.title if playlist else pid


def _device_message(state: JookiState) -> str | None:
    """Return the newest device message type, or None when there are none."""
    if not state.user_messages:
        return None
    return state.user_messages[-1].message_type


def _device_message_attributes(state: JookiState) -> dict[str, Any]:
    """Return id, level, and message type for each device message."""
    return {
        "messages": [
            {
                "id": message.id,
                "level": message.level,
                "message_type": message.message_type,
            }
            for message in state.user_messages
        ]
    }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JookiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jooki sensors from a config entry."""
    client = entry.runtime_data
    async_add_entities([
        JookiSensor(
            client=client,
            entry=entry,
            key="battery",
            name="Battery",
            device_class=SensorDeviceClass.BATTERY,
            native_unit=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda s: s.power.battery_percent,
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="battery_temperature",
            name="Battery Temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda s: s.power.battery_c,
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="figurine",
            name="Figurine",
            icon="mdi:teddy-bear",
            value_fn=lambda s: (
                figurine_label(s, s.nfc.tag_id, s.nfc.star_id) if s.nfc.present else None
            ),
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="wifi_signal",
            name="WiFi Signal",
            device_class=SensorDeviceClass.SIGNAL_STRENGTH,
            native_unit=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda s: s.wifi.signal,
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="wifi_ssid",
            name="WiFi SSID",
            icon="mdi:wifi",
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda s: s.wifi.ssid,
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="bluetooth_speaker_mac",
            name="Bluetooth Speaker MAC",
            icon="mdi:bluetooth",
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda s: s.bluetooth.connected_mac,
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="battery_voltage",
            name="Battery Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            native_unit=UnitOfElectricPotential.MILLIVOLT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda s: s.power.battery_mv if s.power.battery_mv > 0 else None,
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="disk_usage",
            name="Disk Usage",
            icon="mdi:harddisk",
            native_unit=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=_disk_usage_percent,
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="playback_source",
            name="Playback Source",
            icon="mdi:music-box-outline",
            value_fn=_playback_source,
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="current_playlist",
            name="Current Playlist",
            icon="mdi:playlist-music",
            value_fn=_current_playlist,
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="device_message",
            name="Device Message",
            icon="mdi:message-text",
            value_fn=_device_message,
            attributes_fn=_device_message_attributes,
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="nfc_tag_id",
            name="NFC Tag ID",
            icon="mdi:nfc-variant",
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda s: s.nfc.tag_id if s.nfc.present else None,
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="spotify_username",
            name="Spotify Username",
            icon="mdi:spotify",
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda s: s.spotify.username,
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="deezer_username",
            name="Deezer Username",
            icon="mdi:deezer",
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda s: s.deezer.username,
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="firmware",
            name="Firmware",
            icon="mdi:chip",
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda s: s.device.firmware,
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="playlist_count",
            name="Playlist Count",
            icon="mdi:playlist-music",
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda s: len(s.db.playlists),
        ),
        JookiSensor(
            client=client,
            entry=entry,
            key="track_count",
            name="Track Count",
            icon="mdi:music-note-plus",
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda s: len(s.db.tracks),
        ),
    ])


class JookiSensor(SensorEntity):
    """Generic sensor for a Jooki device."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        client: JookiDevice,
        entry: JookiConfigEntry,
        key: str,
        name: str,
        value_fn: Callable[[JookiState], Any],
        device_class: SensorDeviceClass | None = None,
        native_unit: str | None = None,
        state_class: SensorStateClass | None = None,
        icon: str | None = None,
        entity_category: EntityCategory | None = None,
        attributes_fn: Callable[[JookiState], dict[str, Any]] | None = None,
    ) -> None:
        """Initialize the sensor."""
        self._client = client
        self._value_fn = value_fn
        self._attributes_fn = attributes_fn
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = native_unit
        self._attr_state_class = state_class
        self._attr_entity_category = entity_category
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
        )
        if icon:
            self._attr_icon = icon
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
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self._value_fn(self._client.state)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes when this sensor defines them."""
        if self._attributes_fn is None:
            return None
        return self._attributes_fn(self._client.state)
