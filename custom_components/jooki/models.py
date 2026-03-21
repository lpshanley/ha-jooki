"""Data models for the Jooki integration."""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deep_merge(base: dict, update: dict) -> dict:
    """Recursively merge *update* into *base*, mutating and returning *base*.

    Non-dict values (including lists) overwrite rather than merge.
    """
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


# ---------------------------------------------------------------------------
# V2 fine-grained state dataclasses
# ---------------------------------------------------------------------------


@dataclass
class JookiAudioConfig:
    """Audio configuration state (v2: audio.config)."""

    volume: int = 0
    headphones_en: bool = False
    repeat_mode: int = 0  # 0 = off, 1 = all, 2 = one
    shuffle_mode: bool = False


@dataclass
class JookiNowPlaying:
    """Currently playing track metadata (v2: audio.nowPlaying)."""

    track: str | None = None
    artist: str | None = None
    album: str | None = None
    image: str | None = None
    duration_ms: int | None = None
    has_next: bool = False
    has_prev: bool = False
    source: str | None = None
    source_uri: str | None = None
    audiobook: bool = False
    restricted: bool = False
    service: str | None = None
    uri: str | None = None
    playlist_id: str | None = None


@dataclass
class JookiPlaybackInfo:
    """Playback transport state (v2: audio.playback)."""

    state: str = "idle"  # "playing", "paused", "idle" (always lowercase)
    position_ms: int | None = None


@dataclass
class JookiWifiState:
    """WiFi connection state (v2: wifi)."""

    ssid: str | None = None
    bssid: str | None = None
    channel: int | None = None
    signal: int | None = None
    crypt: int | None = None
    stat: str | None = None


@dataclass
class JookiNfcState:
    """NFC/figurine state (v2: nfc)."""

    star_id: str | None = None
    tag_id: str | None = None
    present: bool = False


@dataclass
class JookiSpotifyState:
    """Spotify connection state (v2: spotify)."""

    active: bool = False
    username: str | None = None


@dataclass
class JookiDeviceInfo:
    """Device hardware/firmware info (v2: device)."""

    firmware: str | None = None
    hostname: str | None = None
    device_id: str | None = None
    ip: str | None = None
    machine: str | None = None
    wifi_mac: str | None = None
    disk_usage: dict | None = None
    flags: list[str] | None = None
    toy_safe: bool = False


# ---------------------------------------------------------------------------
# Facade dataclasses (existing entity API — kept for backward compatibility)
# ---------------------------------------------------------------------------


@dataclass
class JookiPowerState:
    """Represents the Jooki's power/battery state."""

    charging: bool = False
    connected: bool = False
    battery_percent: float = 0.0
    battery_mv: int = 0


@dataclass
class JookiPlaybackState:
    """Represents the Jooki's audio playback state.

    This is a *facade* built from the fine-grained v2 dataclasses so that
    existing entity platforms continue to work without modification.
    """

    state: str = "idle"
    volume: int = 0
    track: str | None = None
    album: str | None = None
    position_ms: int | None = None


# ---------------------------------------------------------------------------
# Combined state
# ---------------------------------------------------------------------------


@dataclass
class JookiState:
    """Combined state of a Jooki device.

    For **v1** the entire state is replaced on every MQTT message via
    ``from_json()``.

    For **v2** each message is a partial update containing a single top-level
    key.  Call ``merge_partial()`` to deep-merge it into ``raw`` and rebuild
    the typed dataclasses.
    """

    # -- Facade fields (entity platforms read these) --
    power: JookiPowerState = field(default_factory=JookiPowerState)
    playback: JookiPlaybackState = field(default_factory=JookiPlaybackState)
    available: bool = False
    raw: dict = field(default_factory=dict)

    # -- V2 fine-grained state --
    audio_config: JookiAudioConfig = field(default_factory=JookiAudioConfig)
    now_playing: JookiNowPlaying = field(default_factory=JookiNowPlaying)
    playback_info: JookiPlaybackInfo = field(default_factory=JookiPlaybackInfo)
    wifi: JookiWifiState = field(default_factory=JookiWifiState)
    nfc: JookiNfcState = field(default_factory=JookiNfcState)
    spotify: JookiSpotifyState = field(default_factory=JookiSpotifyState)
    device: JookiDeviceInfo = field(default_factory=JookiDeviceInfo)

    # ------------------------------------------------------------------
    # V1: full-replace (existing behavior)
    # ------------------------------------------------------------------

    @classmethod
    def from_json(cls, payload: dict) -> "JookiState":
        """Parse a complete Jooki v1 state payload into a JookiState."""
        state = cls(available=True, raw=payload)
        state._rebuild_from_raw()
        return state

    # ------------------------------------------------------------------
    # V2: partial deep-merge
    # ------------------------------------------------------------------

    def merge_partial(self, payload: dict) -> None:
        """Deep-merge a v2 partial update into the accumulated raw state."""
        _deep_merge(self.raw, payload)
        self.available = True
        self._rebuild_from_raw()

    # ------------------------------------------------------------------
    # Rebuild typed state from raw dict
    # ------------------------------------------------------------------

    def _rebuild_from_raw(self) -> None:
        """Populate all typed dataclasses from ``self.raw``."""
        self._rebuild_power()
        self._rebuild_audio()
        self._rebuild_wifi()
        self._rebuild_nfc()
        self._rebuild_spotify()
        self._rebuild_device()
        self._rebuild_facade()

    # -- Power ----------------------------------------------------------

    def _rebuild_power(self) -> None:
        power_data = self.raw.get("power", {})
        level_data = power_data.get("level", {})

        # Progressive fields: only overwrite if present in this update,
        # otherwise keep existing values.
        self.power = JookiPowerState(
            charging=power_data.get("charging", self.power.charging),
            connected=power_data.get("connected", self.power.connected),
            battery_percent=level_data.get("p", 0) / 10.0 if "p" in level_data else self.power.battery_percent,
            battery_mv=level_data.get("mv", self.power.battery_mv),
        )

    # -- Audio (config / nowPlaying / playback) -------------------------

    def _rebuild_audio(self) -> None:
        audio_data = self.raw.get("audio", {})

        # audio.config
        config_data = audio_data.get("config", {})
        if config_data:
            self.audio_config = JookiAudioConfig(
                volume=config_data.get("volume", self.audio_config.volume),
                headphones_en=config_data.get("headphones_en", self.audio_config.headphones_en),
                repeat_mode=config_data.get("repeat_mode", self.audio_config.repeat_mode),
                shuffle_mode=config_data.get("shuffle_mode", self.audio_config.shuffle_mode),
            )

        # audio.nowPlaying — two shapes, deep-merged into one dataclass
        np_data = audio_data.get("nowPlaying", {})
        if np_data:
            self.now_playing = JookiNowPlaying(
                track=np_data.get("track", self.now_playing.track),
                artist=np_data.get("artist", self.now_playing.artist),
                album=np_data.get("album", self.now_playing.album),
                image=np_data.get("image", self.now_playing.image),
                duration_ms=np_data.get("duration_ms", self.now_playing.duration_ms),
                has_next=np_data.get("hasNext", self.now_playing.has_next),
                has_prev=np_data.get("hasPrev", self.now_playing.has_prev),
                source=np_data.get("source", self.now_playing.source),
                source_uri=np_data.get("source_uri", self.now_playing.source_uri),
                audiobook=np_data.get("audiobook", self.now_playing.audiobook),
                restricted=np_data.get("restricted", self.now_playing.restricted),
                service=np_data.get("service", self.now_playing.service),
                uri=np_data.get("uri", self.now_playing.uri),
                playlist_id=np_data.get("playlistId", self.now_playing.playlist_id),
            )

        # audio.playback
        playback_data = audio_data.get("playback", {})
        if playback_data:
            raw_state = playback_data.get("state", self.playback_info.state)
            self.playback_info = JookiPlaybackInfo(
                state=raw_state.lower() if isinstance(raw_state, str) else "idle",
                position_ms=playback_data.get("position_ms", self.playback_info.position_ms),
            )

    # -- WiFi -----------------------------------------------------------

    def _rebuild_wifi(self) -> None:
        wifi_data = self.raw.get("wifi", {})
        if wifi_data:
            self.wifi = JookiWifiState(
                ssid=wifi_data.get("ssid"),
                bssid=wifi_data.get("bssid"),
                channel=wifi_data.get("ch"),
                signal=wifi_data.get("signal"),
                crypt=wifi_data.get("crypt"),
                stat=wifi_data.get("stat"),
            )

    # -- NFC ------------------------------------------------------------

    def _rebuild_nfc(self) -> None:
        nfc_data = self.raw.get("nfc")
        if nfc_data is None:
            return  # no nfc key yet — leave defaults

        if isinstance(nfc_data, list):
            # Empty list = no figurine
            self.nfc = JookiNfcState(present=False)
        elif isinstance(nfc_data, dict):
            self.nfc = JookiNfcState(
                star_id=nfc_data.get("starId"),
                tag_id=nfc_data.get("tagId"),
                present=True,
            )

    # -- Spotify --------------------------------------------------------

    def _rebuild_spotify(self) -> None:
        spotify_data = self.raw.get("spotify", {})
        if spotify_data:
            self.spotify = JookiSpotifyState(
                active=spotify_data.get("active", self.spotify.active),
                username=spotify_data.get("username", self.spotify.username),
            )

    # -- Device ---------------------------------------------------------

    def _rebuild_device(self) -> None:
        device_data = self.raw.get("device", {})
        if device_data:
            self.device = JookiDeviceInfo(
                firmware=device_data.get("firmware"),
                hostname=device_data.get("hostname"),
                device_id=device_data.get("id"),
                ip=device_data.get("ip"),
                machine=device_data.get("machine"),
                wifi_mac=device_data.get("wifi_mac"),
                disk_usage=device_data.get("diskUsage"),
                flags=device_data.get("flags"),
                toy_safe=device_data.get("toy_safe", False),
            )

    # -- Facade (backward-compatible JookiPlaybackState) ----------------

    def _rebuild_facade(self) -> None:
        """Rebuild the legacy playback facade from fine-grained state."""
        self.playback = JookiPlaybackState(
            state=self.playback_info.state,
            volume=self.audio_config.volume,
            track=self.now_playing.track,
            album=self.now_playing.album,
            position_ms=self.playback_info.position_ms,
        )
