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
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JookiConfigEntry
from .const import DOMAIN, SIGNAL_STATE_UPDATED
from .models import JookiState
from .mqtt_client import JookiMqttClient


def _disk_usage_percent(state: JookiState) -> int | None:
    """Extract disk usage percentage from device state."""
    du = state.device.disk_usage
    if du and isinstance(du, dict):
        return du.get("usedPercent")
    return None


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
            key="figurine",
            name="Figurine",
            icon="mdi:star-face",
            value_fn=lambda s: s.nfc.star_id if s.nfc.present else None,
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
    ])


class JookiSensor(SensorEntity):
    """Generic sensor for a Jooki device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        client: JookiMqttClient,
        entry: JookiConfigEntry,
        key: str,
        name: str,
        value_fn: Callable[[JookiState], Any],
        device_class: SensorDeviceClass | None = None,
        native_unit: str | None = None,
        state_class: SensorStateClass | None = None,
        icon: str | None = None,
        entity_category: EntityCategory | None = None,
    ) -> None:
        """Initialize the sensor."""
        self._client = client
        self._value_fn = value_fn
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
