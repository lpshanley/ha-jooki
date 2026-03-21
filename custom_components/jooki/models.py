"""Data models for the Jooki integration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class JookiPowerState:
    """Represents the Jooki's power/battery state."""

    charging: bool = False
    connected: bool = False
    battery_percent: float = 0.0
    battery_mv: int = 0


@dataclass
class JookiPlaybackState:
    """Represents the Jooki's audio playback state."""

    state: str = "idle"
    volume: int = 0
    track: str | None = None
    album: str | None = None


@dataclass
class JookiState:
    """Combined state of a Jooki device."""

    power: JookiPowerState = field(default_factory=JookiPowerState)
    playback: JookiPlaybackState = field(default_factory=JookiPlaybackState)
    available: bool = False
    raw: dict | None = None

    @classmethod
    def from_json(cls, payload: dict) -> JookiState:
        """Parse a Jooki state JSON payload into a JookiState."""
        power_data = payload.get("power", {})
        level_data = power_data.get("level", {})
        audio_data = payload.get("audio", {})
        config_data = audio_data.get("config", {})
        playback_data = audio_data.get("playback", {})
        now_playing = audio_data.get("nowPlaying", {})

        power = JookiPowerState(
            charging=power_data.get("charging", False),
            connected=power_data.get("connected", False),
            battery_percent=level_data.get("p", 0) / 10.0,
            battery_mv=level_data.get("mv", 0),
        )

        playback = JookiPlaybackState(
            state=playback_data.get("state", "idle"),
            volume=config_data.get("volume", 0),
            track=now_playing.get("track"),
            album=now_playing.get("album"),
        )

        return cls(
            power=power,
            playback=playback,
            available=True,
            raw=payload,
        )
