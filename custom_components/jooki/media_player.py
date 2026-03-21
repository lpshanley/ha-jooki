"""Media player platform for the Jooki integration."""

from __future__ import annotations

import json
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    RepeatMode,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
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

_REPEAT_MODE_MAP = {
    0: RepeatMode.OFF,
    1: RepeatMode.ALL,
    2: RepeatMode.ONE,
}

_HA_TO_JOOKI_REPEAT = {
    RepeatMode.OFF: 0,
    RepeatMode.ALL: 1,
    RepeatMode.ONE: 2,
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
        | MediaPlayerEntityFeature.REPEAT_SET
        | MediaPlayerEntityFeature.SHUFFLE_SET
    )

    def __init__(self, client: JookiMqttClient, entry: JookiConfigEntry) -> None:
        """Initialize the media player."""
        self._client = client
        self._cfg = client.device_config
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_media_player"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Jooki",
            model=self._cfg.model_name,
            sw_version=self._cfg.version,
        )
        self._signal = SIGNAL_STATE_UPDATED.format(entry.entry_id)
        self._device_info_enriched = False

    async def async_added_to_hass(self) -> None:
        """Subscribe to state updates."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._signal, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        """Handle a state update from the MQTT client."""
        self._enrich_device_info()
        self.async_write_ha_state()

    def _enrich_device_info(self) -> None:
        """Update DeviceInfo with firmware/MAC from device state (once)."""
        if self._device_info_enriched:
            return

        device_state = self._client.state.device
        if not device_state.firmware:
            return

        connections: set[tuple[str, str]] = set()
        if device_state.wifi_mac:
            connections.add((CONNECTION_NETWORK_MAC, device_state.wifi_mac))

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.title,
            manufacturer="Jooki",
            model=self._cfg.model_name,
            sw_version=device_state.firmware,
            hw_version=device_state.machine,
            connections=connections,
        )
        self._device_info_enriched = True

    # ------------------------------------------------------------------
    # State properties
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Media metadata
    # ------------------------------------------------------------------

    @property
    def media_title(self) -> str | None:
        """Return the current track name."""
        return self._client.state.playback.track

    @property
    def media_album_name(self) -> str | None:
        """Return the current album name."""
        return self._client.state.playback.album

    @property
    def media_artist(self) -> str | None:
        """Return the current artist name."""
        return self._client.state.now_playing.artist

    @property
    def media_image_url(self) -> str | None:
        """Return the album art URL."""
        return self._client.state.now_playing.image

    @property
    def media_duration(self) -> int | None:
        """Return the track duration in seconds."""
        dur = self._client.state.now_playing.duration_ms
        if dur is not None:
            return dur // 1000
        return None

    @property
    def media_position(self) -> int | None:
        """Return the current playback position in seconds."""
        pos = self._client.state.playback.position_ms
        if pos is not None:
            return pos // 1000
        return None

    # ------------------------------------------------------------------
    # Repeat / Shuffle
    # ------------------------------------------------------------------

    @property
    def repeat(self) -> RepeatMode | None:
        """Return the current repeat mode."""
        return _REPEAT_MODE_MAP.get(self._client.state.audio_config.repeat_mode)

    @property
    def shuffle(self) -> bool | None:
        """Return the current shuffle state."""
        return self._client.state.audio_config.shuffle_mode

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def async_media_play(self) -> None:
        """Send play command."""
        await self._client.async_publish(self._cfg.topic_do_play, "{}")

    async def async_media_pause(self) -> None:
        """Send pause command."""
        await self._client.async_publish(self._cfg.topic_do_pause, "{}")

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        await self._client.async_publish(self._cfg.topic_do_next, "{}")

    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        await self._client.async_publish(self._cfg.topic_do_prev, "{}")

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level (0.0 to 1.0)."""
        scaled = int(volume * MAX_VOLUME)
        await self._client.async_publish(
            self._cfg.topic_set_vol, json.dumps({"vol": str(scaled)})
        )

    async def async_set_repeat_mode(self, repeat: RepeatMode) -> None:
        """Set repeat mode."""
        mode = _HA_TO_JOOKI_REPEAT.get(repeat, 0)
        await self._client.async_publish(
            self._cfg.topic_set_cfg, json.dumps({"repeat_mode": mode})
        )

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Set shuffle mode."""
        await self._client.async_publish(
            self._cfg.topic_set_cfg, json.dumps({"shuffle_mode": shuffle})
        )

    async def async_turn_off(self) -> None:
        """Shut down the Jooki."""
        await self._client.async_publish(self._cfg.topic_shutdown)
