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
    Platform.BUTTON,
    Platform.EVENT,
    Platform.MEDIA_PLAYER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

# Dispatcher signals (formatted with entry_id)
SIGNAL_STATE_UPDATED = f"{DOMAIN}_state_updated_{{}}"
SIGNAL_NFC_EVENT = f"{DOMAIN}_nfc_event_{{}}"
SIGNAL_BUTTON_EVENT = f"{DOMAIN}_button_event_{{}}"

# Media content types for media browser
MEDIA_TYPE_PLAYLIST = "playlist"
MEDIA_TYPE_FIGURINE = "figurine"
MEDIA_TYPE_TRACK = "track"


# ---------------------------------------------------------------------------
# Version-specific device configuration
# ---------------------------------------------------------------------------

DEVICE_VERSION_V1 = "j1000"
DEVICE_VERSION_V2 = "j2000"
DEVICE_VERSIONS = [DEVICE_VERSION_V1, DEVICE_VERSION_V2]


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

    # MQTT topics — NFC (hardware spoofing: publish to simulate figurine events)
    topic_nfc_tag: str
    topic_nfc_tag_removed: str

    # MQTT topics — GPIO (subscribe for button events)
    topic_gpio_next: str
    topic_gpio_prev: str
    topic_gpio_circle: str


# -- Jooki J1000 (original) ------------------------------------------------

DEVICE_CONFIG_V1 = JookiDeviceConfig(
    version=DEVICE_VERSION_V1,
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
    topic_nfc_tag="/j/nfc/input/tag",
    topic_nfc_tag_removed="/j/nfc/input/tag_removed",
    topic_gpio_next="/j/gpio/input/next",
    topic_gpio_prev="/j/gpio/input/prev",
    topic_gpio_circle="/j/gpio/input/circle",
)

# -- Jooki J2000 (second generation, ml-j2000) -----------------------------

DEVICE_CONFIG_V2 = JookiDeviceConfig(
    version=DEVICE_VERSION_V2,
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
    topic_nfc_tag="/j/nfc/input/tag",
    topic_nfc_tag_removed="/j/nfc/input/tag_removed",
    topic_gpio_next="/j/gpio/input/next",
    topic_gpio_prev="/j/gpio/input/prev",
    topic_gpio_circle="/j/gpio/input/circle",
)

DEVICE_CONFIGS: dict[str, JookiDeviceConfig] = {
    DEVICE_VERSION_V1: DEVICE_CONFIG_V1,
    DEVICE_VERSION_V2: DEVICE_CONFIG_V2,
}


def get_device_config(version: str) -> JookiDeviceConfig:
    """Return the device config for a given version string."""
    return DEVICE_CONFIGS.get(version, DEVICE_CONFIG_V1)
