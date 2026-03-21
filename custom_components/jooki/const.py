"""Constants for the Jooki integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.const import Platform

DOMAIN = "jooki"
DEFAULT_PORT = 1883
DEFAULT_NAME = "Jooki"
MAX_VOLUME = 100
CONF_DEVICE_VERSION = "device_version"

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.LIGHT,
    Platform.MEDIA_PLAYER,
    Platform.SENSOR,
]

# Dispatcher signal (formatted with entry_id)
SIGNAL_STATE_UPDATED = f"{DOMAIN}_state_updated_{{}}"


# ---------------------------------------------------------------------------
# Version-specific device configuration
# ---------------------------------------------------------------------------

DEVICE_VERSION_V1 = "v1"
DEVICE_VERSION_V2 = "v2"
DEVICE_VERSIONS = [DEVICE_VERSION_V1, DEVICE_VERSION_V2]


@dataclass(frozen=True)
class JookiDeviceConfig:
    """Version-specific protocol configuration for a Jooki device."""

    version: str
    model_name: str

    # MQTT topics — state
    topic_state: str

    # MQTT topics — commands
    topic_set_vol: str
    topic_do_play: str
    topic_do_pause: str
    topic_do_next: str
    topic_do_prev: str
    topic_playlist_play: str
    topic_shutdown: str

    # MQTT topics — LEDs
    topic_led_set_raw: str
    topic_led_pulse_raw: str

    # LED identifiers
    led_ids: tuple[str, ...]


# -- Jooki v1 (original) ---------------------------------------------------

DEVICE_CONFIG_V1 = JookiDeviceConfig(
    version=DEVICE_VERSION_V1,
    model_name="Jooki Player (v1)",
    topic_state="/j/web/output/state",
    topic_set_vol="/j/web/input/SET_VOL",
    topic_do_play="/j/web/input/DO_PLAY",
    topic_do_pause="/j/web/input/DO_PAUSE",
    topic_do_next="/j/web/input/DO_NEXT",
    topic_do_prev="/j/web/input/DO_PREV",
    topic_playlist_play="/j/web/input/PLAYLIST_PLAY",
    topic_shutdown="/j/web/input/SHUTDOWN",
    topic_led_set_raw="/j/led/output/set_raw",
    topic_led_pulse_raw="/j/led/output/pulse_raw",
    led_ids=("ALL", "CIRCLE", "NEXT", "VOL_INC", "VOL_DEC", "PREV", "RING"),
)

# -- Jooki v2 (second generation) ------------------------------------------
# TODO: Update these topics/payloads as we discover the v2 protocol.
#       Starting as a copy of v1 — we'll diverge as needed.

DEVICE_CONFIG_V2 = JookiDeviceConfig(
    version=DEVICE_VERSION_V2,
    model_name="Jooki Player (v2)",
    topic_state="/j/web/output/state",
    topic_set_vol="/j/web/input/SET_VOL",
    topic_do_play="/j/web/input/DO_PLAY",
    topic_do_pause="/j/web/input/DO_PAUSE",
    topic_do_next="/j/web/input/DO_NEXT",
    topic_do_prev="/j/web/input/DO_PREV",
    topic_playlist_play="/j/web/input/PLAYLIST_PLAY",
    topic_shutdown="/j/web/input/SHUTDOWN",
    topic_led_set_raw="/j/led/output/set_raw",
    topic_led_pulse_raw="/j/led/output/pulse_raw",
    led_ids=("ALL", "CIRCLE", "NEXT", "VOL_INC", "VOL_DEC", "PREV", "RING"),
)

DEVICE_CONFIGS: dict[str, JookiDeviceConfig] = {
    DEVICE_VERSION_V1: DEVICE_CONFIG_V1,
    DEVICE_VERSION_V2: DEVICE_CONFIG_V2,
}


def get_device_config(version: str) -> JookiDeviceConfig:
    """Return the device config for a given version string."""
    return DEVICE_CONFIGS.get(version, DEVICE_CONFIG_V1)
