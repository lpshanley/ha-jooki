"""Binary sensor platform for the Jooki integration."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JookiConfigEntry
from .const import DOMAIN, SIGNAL_STATE_UPDATED
from .models import JookiState
from .mqtt_client import JookiMqttClient


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JookiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jooki binary sensors from a config entry."""
    client = entry.runtime_data
    async_add_entities([
        JookiBinarySensor(
            client=client,
            entry=entry,
            key="charging",
            name="Charging",
            device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
            value_fn=lambda s: s.power.charging,
        ),
        JookiBinarySensor(
            client=client,
            entry=entry,
            key="plugged_in",
            name="Plugged In",
            device_class=BinarySensorDeviceClass.PLUG,
            value_fn=lambda s: s.power.connected,
        ),
        JookiBinarySensor(
            client=client,
            entry=entry,
            key="headphones",
            name="Headphones",
            device_class=None,
            icon="mdi:headphones",
            value_fn=lambda s: s.audio_config.headphones_en,
        ),
        JookiBinarySensor(
            client=client,
            entry=entry,
            key="figurine_present",
            name="Figurine Present",
            device_class=BinarySensorDeviceClass.PRESENCE,
            value_fn=lambda s: s.nfc.present,
        ),
        JookiBinarySensor(
            client=client,
            entry=entry,
            key="spotify_connected",
            name="Spotify Connected",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            icon="mdi:spotify",
            value_fn=lambda s: s.spotify.active,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
    ])


class JookiBinarySensor(BinarySensorEntity):
    """Generic binary sensor for a Jooki device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        client: JookiMqttClient,
        entry: JookiConfigEntry,
        key: str,
        name: str,
        value_fn: Callable[[JookiState], bool],
        device_class: BinarySensorDeviceClass | None = None,
        icon: str | None = None,
        entity_category: EntityCategory | None = None,
    ) -> None:
        """Initialize the binary sensor."""
        self._client = client
        self._value_fn = value_fn
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_class = device_class
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
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        return self._value_fn(self._client.state)
