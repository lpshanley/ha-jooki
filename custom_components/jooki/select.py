"""Select platform for the Jooki integration (locale select)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JookiConfigEntry
from .const import DOMAIN, SIGNAL_STATE_UPDATED
from .device_commands import JookiDevice
from .models import retained_locale

LOCALE_OPTIONS: dict[str, str] = {
    "English": "en",
    "French": "fr",
    "German": "de",
}

LOCALE_CODE_TO_LABEL: dict[str, str] = {v: k for k, v in LOCALE_OPTIONS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JookiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jooki select entities from a config entry."""
    async_add_entities([JookiLocaleSelect(entry.runtime_data, entry)])


class JookiLocaleSelect(SelectEntity):
    """Select entity to change the Jooki device language."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = "Language"
    _attr_icon = "mdi:translate"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(LOCALE_OPTIONS.keys())

    def __init__(self, client: JookiDevice, entry: JookiConfigEntry) -> None:
        """Initialize the locale select entity."""
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_locale_select"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
        )
        self._signal = SIGNAL_STATE_UPDATED.format(entry.entry_id)
        self._attr_current_option = "English"

    async def async_added_to_hass(self) -> None:
        """Subscribe to state updates."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._signal, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        """Refresh availability without clearing a language the user picked."""
        selected = LOCALE_OPTIONS.get(self._attr_current_option or "")
        code = retained_locale(selected, self._client.state.device.locale)
        label = LOCALE_CODE_TO_LABEL.get(code) if code else None
        if label:
            self._attr_current_option = label
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if the device is available."""
        return self._client.state.available

    async def async_select_option(self, option: str) -> None:
        """Handle the user selecting a language."""
        locale_code = LOCALE_OPTIONS.get(option)
        if locale_code:
            await self._client.async_set_locale(locale_code)
            self._attr_current_option = option
            self.async_write_ha_state()
