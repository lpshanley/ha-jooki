"""Topic and payload encoding for outbound Jooki commands.

This module does not import Home Assistant or paho. Tests load this file by path.
"""

from __future__ import annotations

import json
from typing import Protocol


class CommandTopics(Protocol):
    """Command topic fields read from ``JookiDeviceConfig``."""

    topic_set_vol: str
    topic_do_play: str
    topic_do_pause: str
    topic_do_next: str
    topic_do_prev: str
    topic_playlist_play: str
    topic_shutdown: str
    topic_set_cfg: str
    topic_set_toy_safe: str
    topic_seek: str
    topic_skip_sec: str
    topic_switch_locale: str
    topic_led_set_raw: str
    topic_led_pulse_raw: str
    topic_led_charge_state: str
    topic_nfc_tag: str


def play(config: CommandTopics) -> tuple[str, str]:
    """Return DO_PLAY and an empty JSON object."""
    return config.topic_do_play, "{}"


def pause(config: CommandTopics) -> tuple[str, str]:
    """Return DO_PAUSE and an empty JSON object."""
    return config.topic_do_pause, "{}"


def next_track(config: CommandTopics) -> tuple[str, str]:
    """Return DO_NEXT and an empty JSON object."""
    return config.topic_do_next, "{}"


def previous_track(config: CommandTopics) -> tuple[str, str]:
    """Return DO_PREV and an empty JSON object."""
    return config.topic_do_prev, "{}"


def seek(config: CommandTopics, position: float) -> tuple[str, str]:
    """Return SEEK. ``position`` is seconds; the device wants milliseconds as text."""
    return config.topic_seek, json.dumps({"position_ms": str(position * 1000)})


def set_volume(config: CommandTopics, volume: float, *, scale: int) -> tuple[str, str]:
    """Return SET_VOL for a 0.0 to 1.0 level.

    ``scale`` is ``const.MAX_VOLUME``. The published ``vol`` is that product
    as a decimal string, same as the media player publishes today.
    """
    scaled = int(volume * scale)
    return config.topic_set_vol, json.dumps({"vol": str(scaled)})


def set_repeat_mode(config: CommandTopics, mode: int) -> tuple[str, str]:
    """Return SET_CFG for a device repeat value (0 off, 1 all, 2 one)."""
    return config.topic_set_cfg, json.dumps({"repeat_mode": mode})


def set_shuffle(config: CommandTopics, shuffle: bool) -> tuple[str, str]:
    """Return SET_CFG for shuffle on or off."""
    return config.topic_set_cfg, json.dumps({"shuffle_mode": shuffle})


def shutdown(config: CommandTopics) -> tuple[str, str]:
    """Return SHUTDOWN from the web client."""
    return config.topic_shutdown, json.dumps({"src": "from-web"})


def play_playlist(
    config: CommandTopics, playlist_id: str, track_index: int
) -> tuple[str, str]:
    """Return PLAYLIST_PLAY. ``track_index`` is sent unchanged."""
    return config.topic_playlist_play, json.dumps(
        {"playlistId": playlist_id, "trackIndex": track_index}
    )

