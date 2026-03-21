"""Select platform for the Jooki integration (virtual figurine select)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JookiConfigEntry
from .const import DOMAIN, SIGNAL_STATE_UPDATED
from .mqtt_client import JookiMqttClient

OPTION_NONE = "None"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JookiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jooki select entities from a config entry."""
    async_add_entities([JookiFigurineSelect(entry.runtime_data, entry)])


class JookiFigurineSelect(SelectEntity):
    """Select entity to virtually place/remove a Jooki figurine.

    Options use the format "Name (StarId)" to avoid collisions when
    multiple figurines share the same user-assigned name.  The tag_id
    is resolved via a lookup dict rebuilt on every state update.
    """

    _attr_has_entity_name = True
    _attr_name = "Figurine Select"
    _attr_icon = "mdi:teddy-bear"

    def __init__(self, client: JookiMqttClient, entry: JookiConfigEntry) -> None:
        """Initialize the figurine select entity."""
        self._client = client
        self._cfg = client.device_config
        self._attr_unique_id = f"{entry.entry_id}_figurine_select"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
        )
        self._signal = SIGNAL_STATE_UPDATED.format(entry.entry_id)
        self._attr_options = [OPTION_NONE]
        self._attr_current_option = OPTION_NONE
        # Maps display label → tag_id for reverse lookup on select
        self._label_to_tag: dict[str, str] = {}

    async def async_added_to_hass(self) -> None:
        """Subscribe to state updates."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._signal, self._handle_update)
        )

    def _make_label(self, tag_id: str, name: str, star_id: str | None) -> str:
        """Build a unique display label for a figurine."""
        if star_id:
            return f"{name} ({star_id})"
        return f"{name} ({tag_id[:8]})"

    @callback
    def _handle_update(self) -> None:
        """Handle a state update — refresh options and current selection."""
        db = self._client.state.db
        nfc = self._client.state.nfc

        # Rebuild options and lookup from known tokens
        self._label_to_tag = {}
        labels: list[str] = []
        for tag_id, token in db.tokens.items():
            if not token.name:
                continue
            label = self._make_label(tag_id, token.name, token.star_id)
            labels.append(label)
            self._label_to_tag[label] = tag_id

        self._attr_options = [OPTION_NONE] + sorted(labels)

        # Determine current selection from NFC state
        if nfc.present and nfc.star_id:
            for tag_id, token in db.tokens.items():
                if token.star_id == nfc.star_id:
                    self._attr_current_option = self._make_label(
                        tag_id, token.name, token.star_id
                    )
                    break
            else:
                self._attr_current_option = OPTION_NONE
        else:
            self._attr_current_option = OPTION_NONE

        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if the device is available."""
        return self._client.state.available

    async def async_select_option(self, option: str) -> None:
        """Handle the user selecting a figurine option."""
        if option == OPTION_NONE:
            await self._client.async_publish(self._cfg.topic_nfc_tag_removed, "")
            return

        tag_id = self._label_to_tag.get(option)
        if not tag_id:
            raise HomeAssistantError(
                f"Figurine '{option}' not found in device token registry"
            )

        db = self._client.state.db
        token = db.tokens.get(tag_id)
        star_id = token.star_id if token else "0"
        await self._client.async_publish(
            self._cfg.topic_nfc_tag,
            f"{tag_id},{star_id}",
        )
