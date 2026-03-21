"""Media player platform for the Jooki integration."""

from __future__ import annotations

import json
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JookiConfigEntry
from .const import DOMAIN, MAX_VOLUME, SIGNAL_STATE_UPDATED
from .mqtt_client import JookiMqttClient

_PLAYBACK_STATE_MAP = {
    "playing": MediaPlayerState.PLAYING,
    "paused": MediaPlayerState.PAUSED,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JookiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jooki media player from a config entry."""
    async_add_entities([JookiMediaPlayer(entry.runtime_data, entry)])


class JookiMediaPlayer(MediaPlayerEntity):
    """Representation of a Jooki media player."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.TURN_OFF
    )

    def __init__(self, client: JookiMqttClient, entry: JookiConfigEntry) -> None:
        """Initialize the media player."""
        self._client = client
        self._cfg = client.device_config
        self._attr_unique_id = f"{entry.entry_id}_media_player"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Jooki",
            model=self._cfg.model_name,
            sw_version=self._cfg.version,
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
    def state(self) -> MediaPlayerState | None:
        """Return the current playback state."""
        playback = self._client.state.playback.state
        return _PLAYBACK_STATE_MAP.get(playback, MediaPlayerState.IDLE)

    @property
    def volume_level(self) -> float | None:
        """Return the volume level (0.0 to 1.0)."""
        return self._client.state.playback.volume / MAX_VOLUME

    @property
    def media_title(self) -> str | None:
        """Return the current track name."""
        return self._client.state.playback.track

    @property
    def media_album_name(self) -> str | None:
        """Return the current album name."""
        return self._client.state.playback.album

    async def async_media_play(self) -> None:
        """Send play command."""
        await self._client.async_publish(self._cfg.topic_do_play)

    async def async_media_pause(self) -> None:
        """Send pause command."""
        await self._client.async_publish(self._cfg.topic_do_pause)

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        await self._client.async_publish(self._cfg.topic_do_next)

    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        await self._client.async_publish(self._cfg.topic_do_prev)

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level (0.0 to 1.0)."""
        scaled = int(volume * MAX_VOLUME)
        await self._client.async_publish(
            self._cfg.topic_set_vol, json.dumps({"vol": str(scaled)})
        )

    async def async_turn_off(self) -> None:
        """Shut down the Jooki."""
        await self._client.async_publish(self._cfg.topic_shutdown)
