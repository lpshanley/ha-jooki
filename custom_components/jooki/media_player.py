"""Media player platform for the Jooki integration."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from homeassistant.components.media_player import (
    BrowseMedia,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import utcnow

from . import JookiConfigEntry
from .const import (
    DOMAIN,
    MAX_VOLUME,
    MEDIA_TYPE_FIGURINE,
    MEDIA_TYPE_PLAYLIST,
    MEDIA_TYPE_TRACK,
    SIGNAL_STATE_UPDATED,
)
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
        | MediaPlayerEntityFeature.SEEK
        | MediaPlayerEntityFeature.BROWSE_MEDIA
        | MediaPlayerEntityFeature.PLAY_MEDIA
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
        self._position_updated_at: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to state updates."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._signal, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        """Handle a state update from the MQTT client."""
        self._enrich_device_info()
        # Update position timestamp only when the device reports a position
        if self._client.state.playback.position_ms is not None:
            self._position_updated_at = utcnow()
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

    @property
    def media_position_updated_at(self) -> datetime | None:
        """Return when the position was last updated.

        HA uses this to interpolate the seek bar between updates.
        Stored on each state update rather than computed on read so the
        timestamp is stable between property accesses.
        """
        return self._position_updated_at

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
    # Media browser
    # ------------------------------------------------------------------

    async def async_browse_media(
        self,
        media_content_type: str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Implement the media browser."""
        if media_content_type is None or media_content_id is None:
            return self._build_root_browse()

        if media_content_id == "playlists":
            return self._build_playlists_browse()

        if media_content_id == "figurines":
            return self._build_figurines_browse()

        if media_content_type == MEDIA_TYPE_PLAYLIST:
            return self._build_playlist_detail(media_content_id)

        return self._build_root_browse()

    def _build_root_browse(self) -> BrowseMedia:
        """Build the root media browser with Playlists and Figurines folders."""
        children = [
            BrowseMedia(
                title="Playlists",
                media_class=MediaType.PLAYLIST,
                media_content_type=MEDIA_TYPE_PLAYLIST,
                media_content_id="playlists",
                can_play=False,
                can_expand=True,
                thumbnail=None,
            ),
            BrowseMedia(
                title="Figurines",
                media_class=MediaType.PLAYLIST,
                media_content_type=MEDIA_TYPE_FIGURINE,
                media_content_id="figurines",
                can_play=False,
                can_expand=True,
                thumbnail=None,
            ),
        ]
        return BrowseMedia(
            title="Jooki",
            media_class=MediaType.APP,
            media_content_type="root",
            media_content_id="root",
            can_play=False,
            can_expand=True,
            children=children,
        )

    def _build_playlists_browse(self) -> BrowseMedia:
        """Build the playlists folder listing."""
        db = self._client.state.db
        children = []
        for pid, playlist in db.playlists.items():
            has_tracks = bool(playlist.tracks) or playlist.spotify_uri
            children.append(
                BrowseMedia(
                    title=playlist.title or pid,
                    media_class=MediaType.PLAYLIST,
                    media_content_type=MEDIA_TYPE_PLAYLIST,
                    media_content_id=pid,
                    can_play=has_tracks,
                    can_expand=bool(playlist.tracks),
                    thumbnail=playlist.image,
                )
            )
        return BrowseMedia(
            title="Playlists",
            media_class=MediaType.PLAYLIST,
            media_content_type=MEDIA_TYPE_PLAYLIST,
            media_content_id="playlists",
            can_play=False,
            can_expand=True,
            children=children,
        )

    def _build_figurines_browse(self) -> BrowseMedia:
        """Build the figurines folder listing."""
        db = self._client.state.db
        children = []
        for tid, token in db.tokens.items():
            children.append(
                BrowseMedia(
                    title=f"{token.name} ({token.star_id})" if token.star_id else token.name,
                    media_class=MediaType.PLAYLIST,
                    media_content_type=MEDIA_TYPE_FIGURINE,
                    media_content_id=tid,
                    can_play=True,
                    can_expand=False,
                    thumbnail=None,
                )
            )
        return BrowseMedia(
            title="Figurines",
            media_class=MediaType.PLAYLIST,
            media_content_type=MEDIA_TYPE_FIGURINE,
            media_content_id="figurines",
            can_play=False,
            can_expand=True,
            children=children,
        )

    def _build_playlist_detail(self, playlist_id: str) -> BrowseMedia:
        """Build track listing for a local playlist."""
        db = self._client.state.db
        playlist = db.playlists.get(playlist_id)
        children = []
        if playlist:
            for track_id in playlist.tracks:
                track = db.tracks.get(track_id)
                title = track.title if track else track_id
                children.append(
                    BrowseMedia(
                        title=title,
                        media_class=MediaType.TRACK,
                        media_content_type=MEDIA_TYPE_TRACK,
                        media_content_id=track_id,
                        can_play=False,
                        can_expand=False,
                        thumbnail=None,
                    )
                )
        return BrowseMedia(
            title=playlist.title if playlist else playlist_id,
            media_class=MediaType.PLAYLIST,
            media_content_type=MEDIA_TYPE_PLAYLIST,
            media_content_id=playlist_id,
            can_play=True,
            can_expand=True,
            children=children,
        )

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def async_play_media(
        self,
        media_type: str,
        media_id: str,
        **kwargs: Any,
    ) -> None:
        """Play a playlist or figurine via the PLAYLIST_PLAY command."""
        db = self._client.state.db

        if media_type == MEDIA_TYPE_FIGURINE:
            # Resolve figurine → playlist by matching tag_id
            playlist_id = self._find_playlist_for_token(media_id)
            if playlist_id:
                await self._play_playlist(playlist_id)
                return
            # Fallback: simulate NFC placement if no playlist found
            token = db.tokens.get(media_id)
            if not token:
                raise HomeAssistantError(
                    f"Figurine with tag ID '{media_id}' not found"
                )
            await self._client.async_publish(
                self._cfg.topic_nfc_tag,
                f"{media_id},{token.star_id or '0'}",
            )
            return

        if media_type == MEDIA_TYPE_PLAYLIST:
            if media_id not in db.playlists:
                raise HomeAssistantError(
                    f"Playlist '{media_id}' not found on device"
                )
            await self._play_playlist(media_id)
            return

        raise HomeAssistantError(
            f"Unsupported media type '{media_type}'"
        )

    async def _play_playlist(
        self, playlist_id: str, track_index: int = 0
    ) -> None:
        """Send PLAYLIST_PLAY command to start playback."""
        await self._client.async_publish(
            self._cfg.topic_playlist_play,
            json.dumps({"playlistId": playlist_id, "trackIndex": track_index}),
        )

    def _find_playlist_for_token(self, tag_id: str) -> str | None:
        """Find the playlist bound to a given NFC tag_id."""
        for pid, playlist in self._client.state.db.playlists.items():
            if playlist.tag_id == tag_id:
                return pid
        return None

    async def async_media_seek(self, position: float) -> None:
        """Seek to a position in the current track (seconds)."""
        await self._client.async_publish(
            self._cfg.topic_seek,
            json.dumps({"position_ms": str(position * 1000)}),
        )

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

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
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
        await self._client.async_publish(
            self._cfg.topic_shutdown, json.dumps({"src": "from-web"})
        )
