"""Topic and payload encoding for outbound Jooki commands.

This module does not import Home Assistant or paho. ``JookiMqttClient`` calls
these functions; tests load this file by path. ``JookiDevice`` is the surface
stored on a config entry for platform modules.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:  # path-loaded tests must not execute a package import
    from .models import JookiState


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
    topic_message_dismiss: str
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


def nfc_tag(config: CommandTopics, payload: str) -> tuple[str, str]:
    """Return the NFC tag topic and the payload string unchanged."""
    return config.topic_nfc_tag, payload


def set_toy_safe(config: CommandTopics, enable: bool) -> tuple[str, str]:
    """Return SET_TOY_SAFE for enable true or false."""
    return config.topic_set_toy_safe, json.dumps({"enable": enable})


def set_locale(config: CommandTopics, locale_code: str) -> tuple[str, str]:
    """Return SWITCH_LOCALE for a language code such as ``en``."""
    return config.topic_switch_locale, json.dumps({"locale": locale_code})


def set_led_raw(config: CommandTopics, r: int, g: int, b: int) -> tuple[str, str]:
    """Return set_raw and ``ALL,r,g,b``."""
    return config.topic_led_set_raw, f"ALL,{r},{g},{b}"


def pulse_led(config: CommandTopics, payload: str) -> tuple[str, str]:
    """Return pulse_raw and a wire string the caller already looked up."""
    return config.topic_led_pulse_raw, payload


def set_charge_effect(config: CommandTopics, effect: str) -> tuple[str, str]:
    """Return charge_state and a wire token such as ``BAT_INC``."""
    return config.topic_led_charge_state, effect


def turn_off_led(config: CommandTopics) -> tuple[str, str]:
    """Return set_raw and ``ALL,0,0,0``."""
    return config.topic_led_set_raw, "ALL,0,0,0"


def skip_seconds(config: CommandTopics, delta_s: int) -> tuple[str, str]:
    """Return SKIP_SEC. ``delta_s`` is a number of seconds, negative to go back."""
    return config.topic_skip_sec, json.dumps({"delta_s": delta_s})


def dismiss_message(config: CommandTopics, message_id: int) -> tuple[str, str]:
    """Return MESSAGE_DISMISS for a device message id.

    The player publishes ``userMessages`` again after a successful dismiss,
    so the caller does not drop the message locally.
    """
    return config.topic_message_dismiss, json.dumps({"id": message_id})


class JookiDevice(Protocol):
    """Device operations and read-only state for entity modules."""

    @property
    def state(self) -> JookiState:
        """Current device state."""
        ...

    @property
    def host(self) -> str:
        """Device host address."""
        ...

    @property
    def model_name(self) -> str:
        """Model name for this device family."""
        ...

    async def async_resync(self) -> None:
        """Request a full state dump."""
        ...

    async def async_play(self) -> None:
        """Send play."""
        ...

    async def async_pause(self) -> None:
        """Send pause."""
        ...

    async def async_next_track(self) -> None:
        """Send next track."""
        ...

    async def async_previous_track(self) -> None:
        """Send previous track."""
        ...

    async def async_seek(self, position: float) -> None:
        """Seek to a position in seconds."""
        ...

    async def async_set_volume(self, volume: float) -> None:
        """Set volume from a 0.0 to 1.0 level."""
        ...

    async def async_set_repeat_mode(self, mode: int) -> None:
        """Set repeat mode from the device value 0, 1, or 2."""
        ...

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Set shuffle mode."""
        ...

    async def async_shutdown(self) -> None:
        """Shut down the device."""
        ...

    async def async_play_playlist(self, playlist_id: str, track_index: int) -> None:
        """Play a playlist from ``track_index``."""
        ...

    async def async_send_nfc_tag(self, payload: str) -> None:
        """Send an NFC tag payload string unchanged."""
        ...

    async def async_set_toy_safe(self, enable: bool) -> None:
        """Enable or disable Toy Safe mode."""
        ...

    async def async_set_locale(self, locale_code: str) -> None:
        """Switch the device language."""
        ...

    async def async_set_led_raw(self, r: int, g: int, b: int) -> None:
        """Set the LED ring to an RGB color."""
        ...

    async def async_pulse_led(self, payload: str) -> None:
        """Send a pulse_raw wire string."""
        ...

    async def async_set_charge_effect(self, effect: str) -> None:
        """Send a charge_state token."""
        ...

    async def async_turn_off_led(self) -> None:
        """Turn the LED ring off."""
        ...

    async def async_skip_seconds(self, delta_s: int) -> None:
        """Skip forward or backward by ``delta_s`` seconds."""
        ...

    async def async_dismiss_message(self, message_id: int) -> None:
        """Dismiss a device message by id."""
        ...
