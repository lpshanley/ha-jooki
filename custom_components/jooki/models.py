"""Data models for the Jooki integration."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Top-level slices the player publishes independently. ``audio`` is special:
# config, playback, and nowPlaying replace one at a time.
_AUDIO_KEY = "audio"


def _as_dict(value: object) -> dict:
    """Return a JSON object.

    Empty Lua tables encode as ``[]``. Those are empty maps, not nested data.
    """
    if isinstance(value, dict):
        return value
    return {}


def _replace_slices(base: dict, update: dict) -> None:
    """Replace each slice present in *update*. Sibling slices stay put.

    A present top-level key replaces that value. Keys inside ``audio`` replace
    ``config``, ``playback``, or ``nowPlaying`` without touching the others.
    Nested fields are not merged: an omitted album or playlist is gone.
    """
    for key, value in update.items():
        if key == _AUDIO_KEY:
            if not isinstance(value, dict):
                # ``[]`` is an empty Lua table and carries no audio sub-slice.
                continue
            current = base.get(_AUDIO_KEY)
            if not isinstance(current, dict):
                current = {}
                base[_AUDIO_KEY] = current
            for subkey, subvalue in value.items():
                current[subkey] = subvalue
            continue
        base[key] = value


# Firmware on_tag: msg:match("^(%x+),(%x+)$") and string.len(tagId) == 14.
_NFC_TAG_ID = re.compile(r"^[0-9A-Fa-f]{14}$")
_NFC_STAR_CODE = re.compile(r"^[0-9A-Fa-f]+$")


def nfc_tag_payload(tag_id: str | None, star_code: str | None) -> str | None:
    """Return ``tagId,starHex`` for ``/j/nfc/input/tag``, or None.

    A star name such as ``Jooki.Dragon`` is not a wire star code.
    """
    if not isinstance(tag_id, str) or not isinstance(star_code, str):
        return None
    if _NFC_TAG_ID.fullmatch(tag_id) is None:
        return None
    if _NFC_STAR_CODE.fullmatch(star_code) is None:
        return None
    return f"{tag_id},{star_code}"


def playlist_id_for_figurine(
    playlists: dict[str, JookiPlaylist], identifier: str
) -> str | None:
    """Resolve a playlist by ``tagId``, or by ``star`` when it has no tag.

    Matches Catalog.lua ``star2playlist``: a star link is only used when
    the playlist is not bound to a specific tag.
    """
    for playlist_id, playlist in playlists.items():
        if playlist.tag_id == identifier:
            return playlist_id
    for playlist_id, playlist in playlists.items():
        if not playlist.tag_id and playlist.star == identifier:
            return playlist_id
    return None


def retained_locale(selected: str | None, device_locale: str | None) -> str | None:
    """Keep the user's locale when a device slice does not report one.

    SWITCH_LOCALE is not echoed on success, and device slices omit locale.
    A missing value must not replace the choice with a default language.
    """
    if isinstance(device_locale, str) and device_locale:
        return device_locale
    return selected


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
    locale: str | None = None


@dataclass
class JookiPlaylist:
    """A single playlist entry from the device content database."""

    playlist_id: str = ""
    title: str = ""
    image: str | None = None
    tag_id: str | None = None
    star: str | None = None
    audiobook: bool = False
    tracks: list[str] = field(default_factory=list)
    # Spotify-linked playlists
    spotify_source: str | None = None
    spotify_uri: str | None = None


@dataclass
class JookiToken:
    """An NFC token/figurine from the device content database."""

    tag_id: str = ""
    name: str = ""
    star_id: str | None = None
    seen: int | None = None  # Play count (number of times figurine placed)


@dataclass
class JookiTrack:
    """A local track from the device content database."""

    track_id: str = ""
    title: str = ""
    artist: str | None = None
    album: str | None = None
    duration: int | None = None  # Duration in SECONDS (not milliseconds)
    filename: str | None = None
    format: str | None = None  # e.g. "ID3 tag" for MP3
    has_image: bool = False
    size: int | None = None  # File size in bytes


@dataclass
class JookiDatabaseState:
    """Device content database state (v2: db)."""

    playlists: dict[str, JookiPlaylist] = field(default_factory=dict)
    tokens: dict[str, JookiToken] = field(default_factory=dict)
    tracks: dict[str, JookiTrack] = field(default_factory=dict)


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

    J1000 and J2000 publish the same partial slices. ``apply_slices()``
    replaces each slice whose key is present, leaves sibling slices in
    ``raw``, and rebuilds only the typed fields for keys in that payload.
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
    db: JookiDatabaseState = field(default_factory=JookiDatabaseState)

    @classmethod
    def from_json(cls, payload: dict) -> "JookiState":
        """Parse a payload by replacing each slice that is present."""
        state = cls()
        state.apply_slices(payload)
        return state

    def apply_slices(self, payload: dict) -> None:
        """Replace each slice present in *payload* and rebuild those slices.

        Sets ``available``. Only top-level keys in *payload* are rebuilt.
        ``audio`` rebuilds audio and the playback facade. ``power``,
        ``wifi``, ``nfc``, ``spotify``, ``device``, and ``db`` each rebuild
        only themselves, so a wifi update does not rebuild the catalog.
        """
        _replace_slices(self.raw, payload)
        self.available = True
        if "power" in payload:
            self._rebuild_power()
        if _AUDIO_KEY in payload:
            self._rebuild_audio()
            self._rebuild_facade()
        if "wifi" in payload:
            self._rebuild_wifi()
        if "nfc" in payload:
            self._rebuild_nfc()
        if "spotify" in payload:
            self._rebuild_spotify()
        if "device" in payload:
            self._rebuild_device()
        if "db" in payload:
            self._rebuild_db()

    def apply_gstreamer_audio(
        self, event: str, payload: dict | None = None
    ) -> str | None:
        """Record a local GStreamer audio event on ``audio.playback``.

        ``/j/audio/input/position`` payloads are ``{"id": N, "pos": N}`` with
        ``pos`` in milliseconds. The same integer position returns None and
        does not rebuild. A new position writes ``audio.playback.position_ms``
        and updates ``playback_info.position_ms`` and the facade
        ``playback.position_ms`` in place, then returns ``"position"``.
        ``playing``, ``paused``, ``stopped``, and ``ended`` update raw
        playback, rebuild audio and the facade only, and return
        ``"transport"``. ``ended`` clears ``position_ms``. Invalid payloads
        return None.
        """
        if event == "position":
            if not isinstance(payload, dict) or "pos" not in payload:
                return None
            try:
                pos = int(payload["pos"])
            except (TypeError, ValueError):
                return None
            audio = self.raw.get("audio")
            playback = audio.get("playback") if isinstance(audio, dict) else None
            stored = (
                playback.get("position_ms") if isinstance(playback, dict) else None
            )
            # ``bool`` is an ``int`` subclass; a jack-like flag is not a position.
            if not isinstance(stored, bool) and stored == pos:
                return None
            playback_raw = self._ensure_audio_playback()
            playback_raw["position_ms"] = pos
            self.playback_info.position_ms = pos
            self.playback.position_ms = pos
            return "position"

        if event in {"playing", "paused", "stopped", "ended"}:
            playback_raw = self._ensure_audio_playback()
            playback_raw["state"] = event
            if event == "ended":
                playback_raw["position_ms"] = None
            self._rebuild_audio()
            self._rebuild_facade()
            return "transport"

        return None

    def apply_hp_plugged(self, payload: str) -> bool:
        """Record a J2000 headphone jack event on ``audio.config``.

        ``/j/gpio/input/hp_plugged`` is ``"1"`` when plugged in and ``"0"``
        when removed. The same stored value, and any other payload, returns
        False and does not rebuild. A change writes raw and rebuilds audio
        and the facade only.
        """
        value = str(payload).strip()
        if value not in {"0", "1"}:
            return False
        enabled = value == "1"
        audio = self.raw.get("audio")
        config = audio.get("config") if isinstance(audio, dict) else None
        if isinstance(config, dict) and config.get("headphones_en") == enabled:
            return False

        if not isinstance(audio, dict):
            audio = {}
            self.raw["audio"] = audio
        if not isinstance(config, dict):
            config = {}
            audio["config"] = config
        config["headphones_en"] = enabled
        self._rebuild_audio()
        self._rebuild_facade()
        return True

    def _ensure_audio_playback(self) -> dict:
        """Return raw ``audio.playback``, creating the objects if needed."""
        audio = self.raw.get("audio")
        if not isinstance(audio, dict):
            audio = {}
            self.raw["audio"] = audio
        playback = audio.get("playback")
        if not isinstance(playback, dict):
            playback = {}
            audio["playback"] = playback
        return playback

    # ------------------------------------------------------------------
    # Rebuild one typed slice from raw. Callers rebuild only the slice
    # that changed, so a wifi or position tick does not replace the catalog.
    # ------------------------------------------------------------------

    # -- Power ----------------------------------------------------------

    def _rebuild_power(self) -> None:
        power_data = self.raw.get("power")
        if not isinstance(power_data, dict):
            self.power = JookiPowerState()
            return

        level_data = power_data.get("level")
        if not isinstance(level_data, dict):
            level_data = {}

        # ``p`` is tenths of a percent (1000 = 100.0%). Omitted fields belong
        # to this replaced slice, so they do not keep the previous reading.
        if "p" in level_data:
            battery_percent = level_data["p"] / 10.0
        else:
            battery_percent = 0.0
        self.power = JookiPowerState(
            charging=bool(power_data.get("charging", False)),
            connected=bool(power_data.get("connected", False)),
            battery_percent=battery_percent,
            battery_mv=level_data.get("mv", 0) or 0,
        )

    # -- Audio (config / nowPlaying / playback) -------------------------

    def _rebuild_audio(self) -> None:
        audio_data = self.raw.get("audio")
        if not isinstance(audio_data, dict):
            audio_data = {}

        config_data = audio_data.get("config")
        if isinstance(config_data, dict):
            self.audio_config = JookiAudioConfig(
                volume=config_data.get("volume", 0) or 0,
                headphones_en=bool(config_data.get("headphones_en", False)),
                repeat_mode=config_data.get("repeat_mode", 0) or 0,
                shuffle_mode=bool(config_data.get("shuffle_mode", False)),
            )
        else:
            self.audio_config = JookiAudioConfig()

        np_data = audio_data.get("nowPlaying")
        if isinstance(np_data, dict):
            self.now_playing = JookiNowPlaying(
                track=np_data.get("track"),
                artist=np_data.get("artist"),
                album=np_data.get("album"),
                image=np_data.get("image") or None,
                duration_ms=np_data.get("duration_ms"),
                has_next=bool(np_data.get("hasNext", False)),
                has_prev=bool(np_data.get("hasPrev", False)),
                source=np_data.get("source"),
                source_uri=np_data.get("source_uri"),
                audiobook=bool(np_data.get("audiobook", False)),
                restricted=bool(np_data.get("restricted", False)),
                service=np_data.get("service"),
                uri=np_data.get("uri"),
                playlist_id=np_data.get("playlistId"),
            )
        else:
            self.now_playing = JookiNowPlaying()

        playback_data = audio_data.get("playback")
        if isinstance(playback_data, dict):
            raw_state = playback_data.get("state", "idle")
            self.playback_info = JookiPlaybackInfo(
                state=raw_state.lower() if isinstance(raw_state, str) else "idle",
                position_ms=playback_data.get("position_ms"),
            )
        else:
            self.playback_info = JookiPlaybackInfo()

    # -- WiFi -----------------------------------------------------------

    def _rebuild_wifi(self) -> None:
        wifi_data = self.raw.get("wifi")
        if isinstance(wifi_data, dict):
            self.wifi = JookiWifiState(
                ssid=wifi_data.get("ssid"),
                bssid=wifi_data.get("bssid"),
                channel=wifi_data.get("ch"),
                signal=wifi_data.get("signal"),
                crypt=wifi_data.get("crypt"),
                stat=wifi_data.get("stat"),
            )
        else:
            self.wifi = JookiWifiState()

    # -- NFC ------------------------------------------------------------

    def _rebuild_nfc(self) -> None:
        if "nfc" not in self.raw:
            self.nfc = JookiNfcState()
            return

        nfc_data = self.raw.get("nfc")
        if isinstance(nfc_data, dict):
            self.nfc = JookiNfcState(
                star_id=nfc_data.get("starId"),
                tag_id=nfc_data.get("tagId"),
                present=True,
            )
        else:
            # ``[]`` is an empty Lua table: no figurine on the reader.
            self.nfc = JookiNfcState(present=False)

    # -- Spotify --------------------------------------------------------

    def _rebuild_spotify(self) -> None:
        spotify_data = self.raw.get("spotify")
        if isinstance(spotify_data, dict):
            self.spotify = JookiSpotifyState(
                active=bool(spotify_data.get("active", False)),
                username=spotify_data.get("username"),
            )
        else:
            self.spotify = JookiSpotifyState()

    # -- Device ---------------------------------------------------------

    def _rebuild_device(self) -> None:
        device_data = self.raw.get("device")
        if isinstance(device_data, dict):
            self.device = JookiDeviceInfo(
                firmware=device_data.get("firmware"),
                hostname=device_data.get("hostname"),
                device_id=device_data.get("id"),
                ip=device_data.get("ip"),
                machine=device_data.get("machine"),
                wifi_mac=device_data.get("wifi_mac"),
                disk_usage=device_data.get("diskUsage"),
                flags=device_data.get("flags"),
                toy_safe=bool(device_data.get("toy_safe", False)),
            )
        else:
            self.device = JookiDeviceInfo()

    # -- Database (playlists / tokens / tracks) ---------------------------

    def _rebuild_db(self) -> None:
        db_data = self.raw.get("db")
        if not isinstance(db_data, dict):
            self.db = JookiDatabaseState()
            return

        playlists: dict[str, JookiPlaylist] = {}
        for pid, pdata in _as_dict(db_data.get("playlists")).items():
            if not isinstance(pdata, dict):
                continue
            spotify_data = pdata.get("spotify")
            if not isinstance(spotify_data, dict):
                spotify_data = {}
            playlists[pid] = JookiPlaylist(
                playlist_id=pid,
                title=pdata.get("title", ""),
                image=pdata.get("image"),
                tag_id=pdata.get("tagId"),
                star=pdata.get("star"),
                audiobook=bool(pdata.get("audiobook", False)),
                tracks=pdata.get("tracks") or [],
                spotify_source=spotify_data.get("source"),
                spotify_uri=spotify_data.get("uri"),
            )

        tokens: dict[str, JookiToken] = {}
        for tid, tdata in _as_dict(db_data.get("tokens")).items():
            if not isinstance(tdata, dict):
                continue
            tokens[tid] = JookiToken(
                tag_id=tid,
                name=tdata.get("name", ""),
                star_id=tdata.get("starId"),
                seen=tdata.get("seen"),
            )

        tracks: dict[str, JookiTrack] = {}
        for trid, trdata in _as_dict(db_data.get("tracks")).items():
            if not isinstance(trdata, dict):
                continue
            tracks[trid] = JookiTrack(
                track_id=trid,
                title=trdata.get("title", ""),
                artist=trdata.get("artist"),
                album=trdata.get("album"),
                duration=trdata.get("duration"),
                filename=trdata.get("filename"),
                format=trdata.get("format2"),
                has_image=bool(trdata.get("hasImage", False)),
                size=trdata.get("size"),
            )

        self.db = JookiDatabaseState(
            playlists=playlists, tokens=tokens, tracks=tracks
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
