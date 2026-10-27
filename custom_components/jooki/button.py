"""Button platform for the Jooki integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JookiConfigEntry
from .const import DOMAIN, SIGNAL_STATE_UPDATED
from .device_commands import JookiDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JookiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jooki buttons from a config entry."""
    async_add_entities([JookiResyncButton(entry.runtime_data, entry)])


class JookiResyncButton(ButtonEntity):
    """Button to resync state from the Jooki device."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = "Resync"
    _attr_icon = "mdi:sync"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, client: JookiDevice, entry: JookiConfigEntry) -> None:
        """Initialize the resync button."""
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_resync"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
        )
        self._signal = SIGNAL_STATE_UPDATED.format(entry.entry_id)

    async def async_added_to_hass(self) -> None:
        """Record availability and subscribe to later changes."""
        self._seen_available = self._client.state.available
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self._signal, self._handle_availability
            )
        )

    @callback
    def _handle_availability(self) -> None:
        """Write HA state only when device availability changes."""
        available = self._client.state.available
        if available == self._seen_available:
            return
        self._seen_available = available
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if the device is available."""
        return self._client.state.available

    async def async_press(self) -> None:
        """Handle the button press — send CONNECT + GET_STATE."""
        await self._client.async_resync()
