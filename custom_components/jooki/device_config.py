"""MQTT topic map for each Jooki device version.

This module does not import Home Assistant or paho. Tests load it by path.
``version`` uses the same ids as ``const.DEVICE_VERSION_V1`` and
``const.DEVICE_VERSION_V2`` (``j1000`` and ``j2000``).
"""

from __future__ import annotations

from dataclasses import dataclass

# Same ids as const.DEVICE_VERSION_V1 and const.DEVICE_VERSION_V2.
_VERSION_V1 = "j1000"
_VERSION_V2 = "j2000"


@dataclass(frozen=True)
class JookiDeviceConfig:
    """Version-specific protocol configuration for a Jooki device."""

    version: str
    model_name: str

    # MQTT topics — state
    topic_state: str
    topic_error: str

    # MQTT topics — commands
    topic_set_vol: str
    topic_do_play: str
    topic_do_pause: str
    topic_do_next: str
    topic_do_prev: str
    topic_playlist_play: str
    topic_shutdown: str
    topic_set_cfg: str
    topic_get_state: str
    topic_connect: str
    topic_set_toy_safe: str
    topic_seek: str
    topic_skip_sec: str
    topic_message_dismiss: str
    topic_switch_locale: str

    # MQTT topics — LED
    topic_led_set_raw: str
    topic_led_pulse_raw: str
    topic_led_charge_state: str

    # MQTT topics — NFC (hardware spoofing: publish to simulate figurine events)
    topic_nfc_tag: str
    topic_nfc_tag_removed: str

    # MQTT topics — GPIO (subscribe for button/knob events)
    topic_gpio_next: str
    topic_gpio_prev: str
    topic_gpio_circle: str
    topic_gpio_vol_set: str

    # MQTT topics — Audio (subscribe for playback events)
    topic_audio_position: str
    topic_audio_playing: str
    topic_audio_paused: str
    topic_audio_stopped: str
    topic_audio_error: str
    topic_audio_ended: str

    # J2000 headphone jack. Left unset on J1000 so the topic table is shared.
    topic_gpio_hp_plugged: str | None = None


# -- Jooki J1000 (original) ------------------------------------------------

DEVICE_CONFIG_V1 = JookiDeviceConfig(
    version=_VERSION_V1,
    model_name="Jooki J1000",
    topic_state="/j/web/output/state",
    topic_error="/j/web/output/error",
    topic_set_vol="/j/web/input/SET_VOL",
    topic_do_play="/j/web/input/DO_PLAY",
    topic_do_pause="/j/web/input/DO_PAUSE",
    topic_do_next="/j/web/input/DO_NEXT",
    topic_do_prev="/j/web/input/DO_PREV",
    topic_playlist_play="/j/web/input/PLAYLIST_PLAY",
    topic_shutdown="/j/web/input/SHUTDOWN",
    topic_set_cfg="/j/web/input/SET_CFG",
    topic_get_state="/j/web/input/GET_STATE",
    topic_connect="/j/web/input/CONNECT",
    topic_set_toy_safe="/j/web/input/SET_TOY_SAFE",
    topic_seek="/j/web/input/SEEK",
    topic_skip_sec="/j/web/input/SKIP_SEC",
    topic_message_dismiss="/j/web/input/MESSAGE_DISMISS",
    topic_switch_locale="/j/web/input/SWITCH_LOCALE",
    topic_led_set_raw="/j/led/output/set_raw",
    topic_led_pulse_raw="/j/led/output/pulse_raw",
    topic_led_charge_state="/j/led/output/charge_state",
    topic_nfc_tag="/j/nfc/input/tag",
    topic_nfc_tag_removed="/j/nfc/input/tag_removed",
    topic_gpio_next="/j/gpio/input/next",
    topic_gpio_prev="/j/gpio/input/prev",
    topic_gpio_circle="/j/gpio/input/circle",
    topic_gpio_vol_set="/j/gpio/input/vol_set",
    topic_audio_position="/j/audio/input/position",
    topic_audio_playing="/j/audio/input/playing",
    topic_audio_paused="/j/audio/input/paused",
    topic_audio_stopped="/j/audio/input/stopped",
    topic_audio_error="/j/audio/input/error",
    topic_audio_ended="/j/audio/input/ended",
)

# -- Jooki J2000 (second generation, ml-j2000) -----------------------------

DEVICE_CONFIG_V2 = JookiDeviceConfig(
    version=_VERSION_V2,
    model_name="Jooki J2000",
    topic_state="/j/web/output/state",
    topic_error="/j/web/output/error",
    topic_set_vol="/j/web/input/SET_VOL",
    topic_do_play="/j/web/input/DO_PLAY",
    topic_do_pause="/j/web/input/DO_PAUSE",
    topic_do_next="/j/web/input/DO_NEXT",
    topic_do_prev="/j/web/input/DO_PREV",
    topic_playlist_play="/j/web/input/PLAYLIST_PLAY",
    topic_shutdown="/j/web/input/SHUTDOWN",
    topic_set_cfg="/j/web/input/SET_CFG",
    topic_get_state="/j/web/input/GET_STATE",
    topic_connect="/j/web/input/CONNECT",
    topic_set_toy_safe="/j/web/input/SET_TOY_SAFE",
    topic_seek="/j/web/input/SEEK",
    topic_skip_sec="/j/web/input/SKIP_SEC",
    topic_message_dismiss="/j/web/input/MESSAGE_DISMISS",
    topic_switch_locale="/j/web/input/SWITCH_LOCALE",
    topic_led_set_raw="/j/led/output/set_raw",
    topic_led_pulse_raw="/j/led/output/pulse_raw",
    topic_led_charge_state="/j/led/output/charge_state",
    topic_nfc_tag="/j/nfc/input/tag",
    topic_nfc_tag_removed="/j/nfc/input/tag_removed",
    topic_gpio_next="/j/gpio/input/next",
    topic_gpio_prev="/j/gpio/input/prev",
    topic_gpio_circle="/j/gpio/input/circle",
    topic_gpio_vol_set="/j/gpio/input/vol_set",
    topic_audio_position="/j/audio/input/position",
    topic_audio_playing="/j/audio/input/playing",
    topic_audio_paused="/j/audio/input/paused",
    topic_audio_stopped="/j/audio/input/stopped",
    topic_audio_error="/j/audio/input/error",
    topic_audio_ended="/j/audio/input/ended",
    topic_gpio_hp_plugged="/j/gpio/input/hp_plugged",
)

DEVICE_CONFIGS: dict[str, JookiDeviceConfig] = {
    DEVICE_CONFIG_V1.version: DEVICE_CONFIG_V1,
    DEVICE_CONFIG_V2.version: DEVICE_CONFIG_V2,
}


def get_device_config(version: str) -> JookiDeviceConfig:
    """Return the device config for a given version string."""
    return DEVICE_CONFIGS.get(version, DEVICE_CONFIG_V1)
