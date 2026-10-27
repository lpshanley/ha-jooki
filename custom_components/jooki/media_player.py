"""Media player platform for the Jooki integration."""

from __future__ import annotations

from datetime import datetime, timedelta
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
    SIGNAL_POSITION_UPDATED,
    SIGNAL_STATE_UPDATED,
)
from .device_commands import JookiDevice
from .models import JookiPlaylist, nfc_tag_payload, playlist_id_for_figurine

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

# A seek is a jump from the previous tick, not from the last written sample.
# Ordinary playback would otherwise cross 2000 ms and look like a seek.
_POSITION_SEEK_THRESHOLD_MS = 2000
_POSITION_WRITE_INTERVAL = timedelta(seconds=10)


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

    def __init__(self, client: JookiDevice, entry: JookiConfigEntry) -> None:
        """Initialize the media player."""
        self._client = client
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_media_player"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Jooki",
            model=client.model_name,
        )
        self._signal = SIGNAL_STATE_UPDATED.format(entry.entry_id)
        self._position_signal = SIGNAL_POSITION_UPDATED.format(entry.entry_id)
        self._device_info_enriched = False
        self._position_updated_at: datetime | None = None
        self._last_position_ms: int | None = None
        self._last_seen_position_ms: int | None = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to state and position updates."""
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._signal, self._handle_update)
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self._position_signal, self._handle_position
            )
        )

    @callback
    def _handle_update(self) -> None:
        """Write transport, metadata, volume, and web playback updates.

        Position-only GStreamer ticks use ``_handle_position`` instead.
        """
        self._enrich_device_info()
        # Anchor interpolation when this write publishes a new position.
        # Leave the timestamp alone when the position is unchanged so a
        # volume or metadata write does not restart the seek bar.
        # A cleared position drops the anchor so the next track's first
        # tick is written instead of looking like a small step.
        pos = self._client.state.playback.position_ms
        if pos is None:
            self._last_position_ms = None
            self._last_seen_position_ms = None
            self._position_updated_at = None
        elif pos != self._last_position_ms:
            self._last_position_ms = pos
            self._last_seen_position_ms = pos
            self._position_updated_at = utcnow()
        self.async_write_ha_state()

    @callback
    def _handle_position(self) -> None:
        """Write a seek immediately, and otherwise at most every 10 seconds."""
        pos = self._client.state.playback.position_ms
        if pos is None:
            return
        previous = self._last_seen_position_ms
        self._last_seen_position_ms = pos
        if not self._position_sample_due(previous, pos):
            return
        self._last_position_ms = pos
        self._position_updated_at = utcnow()
        self.async_write_ha_state()

    def _position_sample_due(self, previous: int | None, pos: int) -> bool:
        """Return True for a seek, the first sample, or a 10 second sample."""
        if previous is None:
            return True
        if abs(pos - previous) >= _POSITION_SEEK_THRESHOLD_MS:
            return True
        updated_at = self._position_updated_at
        if updated_at is None:
            return True
        return utcnow() - updated_at >= _POSITION_WRITE_INTERVAL

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
            model=self._client.model_name,
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
        """Return the album art URL.

        Spotify images are full URLs. Local track artwork uses relative
        paths like ``/artwork/hash.jpg`` which need the device host prepended.
        """
        image = self._client.state.now_playing.image
        if not isinstance(image, str):
            return None
        if image.startswith("/"):
            return f"http://{self._client.host}{image}"
        return image

    @property
    def media_duration(self) -> int | None:
        """Return the track duration in seconds."""
        dur = self._client.state.now_playing.duration_ms
        if dur is not None:
            return dur // 1000
        return None

    @property
    def media_position(self) -> float | None:
        """Return the current playback position in seconds."""
        pos = self._client.state.playback.position_ms
        if pos is not None:
            return pos / 1000
        return None

    @property
    def media_position_updated_at(self) -> datetime | None:
        """Return when the last written position sample was taken.

        Home Assistant interpolates the seek bar from this timestamp.
        Position ticks change it only when that tick is written. A state
        write changes it when the published position changes.
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
        """Implement the media browser.

        Flat layout: all playlists at the root level (no sub-folders).
        The TRASH system playlist is renamed to "Unassigned" in the UI.
        """
        if media_content_type == MEDIA_TYPE_PLAYLIST and media_content_id:
            return self._build_playlist_detail(media_content_id)

        return self._build_root_browse()

    def _playlist_display_title(self, pid: str, playlist: JookiPlaylist) -> str:
        """Return a display title, renaming the TRASH system playlist."""
        if pid == "TRASH":
            return "Unassigned"
        return playlist.title or pid

    def _build_root_browse(self) -> BrowseMedia:
        """Build a flat root listing of all playlists."""
        db = self._client.state.db
        children = []
        for pid, playlist in db.playlists.items():
            has_tracks = bool(playlist.tracks) or playlist.spotify_uri
            children.append(
                BrowseMedia(
                    title=self._playlist_display_title(pid, playlist),
                    media_class=MediaType.PLAYLIST,
                    media_content_type=MEDIA_TYPE_PLAYLIST,
                    media_content_id=pid,
                    can_play=has_tracks,
                    can_expand=bool(playlist.tracks),
                    thumbnail=playlist.image,
                )
            )
        return BrowseMedia(
            title="Jooki",
            media_class=MediaType.APP,
            media_content_type="root",
            media_content_id="root",
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
                        can_play=True,
                        can_expand=False,
                        thumbnail=None,
                    )
                )
        detail_title = (
            self._playlist_display_title(playlist_id, playlist)
            if playlist
            else playlist_id
        )
        return BrowseMedia(
            title=detail_title,
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
        """Play a playlist, track, or figurine.

        Playlists use PLAYLIST_PLAY. A figurine resolves by tag id or star
        first; NFC spoofing is only used for a valid tag and hex star code.
        """
        db = self._client.state.db

        if media_type == MEDIA_TYPE_FIGURINE:
            playlist_id = playlist_id_for_figurine(db.playlists, media_id)
            if playlist_id:
                await self._play_playlist(playlist_id)
                return
            token = db.tokens.get(media_id)
            payload = nfc_tag_payload(media_id, token.star_id if token else None)
            if payload is None:
                raise HomeAssistantError(
                    f"Figurine '{media_id}' has no matching playlist and is not a valid NFC tag"
                )
            await self._client.async_send_nfc_tag(payload)
            return

        if media_type == MEDIA_TYPE_PLAYLIST:
            if media_id not in db.playlists:
                raise HomeAssistantError(
                    f"Playlist '{media_id}' not found on device"
                )
            await self._play_playlist(media_id)
            return

        if media_type == MEDIA_TYPE_TRACK:
            await self._play_track(media_id)
            return

        raise HomeAssistantError(
            f"Unsupported media type '{media_type}'"
        )

    async def _play_playlist(
        self, playlist_id: str, track_index: int | None = None
    ) -> None:
        """Play a playlist via PLAYLIST_PLAY.

        Local playlists use 1-based trackIndex.
        Spotify playlists use 0-based trackIndex.
        """
        if track_index is None:
            db = self._client.state.db
            playlist = db.playlists.get(playlist_id)
            track_index = 0 if (playlist and playlist.spotify_uri) else 1

        await self._client.async_play_playlist(playlist_id, track_index)

    async def _play_track(self, track_id: str) -> None:
        """Find which playlist contains a track and play from that index."""
        db = self._client.state.db
        for pid, playlist in db.playlists.items():
            if track_id in playlist.tracks:
                # Local playlists are 1-based
                index = playlist.tracks.index(track_id) + 1
                await self._play_playlist(pid, track_index=index)
                return
        raise HomeAssistantError(f"Track '{track_id}' not found in any playlist")

    async def async_media_seek(self, position: float) -> None:
        """Seek to a position in the current track (seconds)."""
        await self._client.async_seek(position)

    async def async_media_play(self) -> None:
        """Send play command."""
        await self._client.async_play()

    async def async_media_pause(self) -> None:
        """Send pause command."""
        await self._client.async_pause()

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        await self._client.async_next_track()

    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        await self._client.async_previous_track()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level (0.0 to 1.0)."""
        await self._client.async_set_volume(volume)

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        """Set repeat mode."""
        mode = _HA_TO_JOOKI_REPEAT.get(repeat, 0)
        await self._client.async_set_repeat_mode(mode)

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Set shuffle mode."""
        await self._client.async_set_shuffle(shuffle)

    async def async_turn_off(self) -> None:
        """Shut down the Jooki."""
        await self._client.async_shutdown()
