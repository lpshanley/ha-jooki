"""Constants for the Jooki integration."""

from __future__ import annotations

from homeassistant.const import Platform

from .device_config import JookiDeviceConfig, get_device_config

DOMAIN = "jooki"
DEFAULT_PORT = 1883
DEFAULT_NAME = "Jooki"
MAX_VOLUME = 100
CONF_DEVICE_VERSION = "device_version"

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.LIGHT,
    Platform.MEDIA_PLAYER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

# Dispatcher signals (formatted with entry_id)
SIGNAL_STATE_UPDATED = f"{DOMAIN}_state_updated_{{}}"
SIGNAL_NFC_EVENT = f"{DOMAIN}_nfc_event_{{}}"
SIGNAL_BUTTON_EVENT = f"{DOMAIN}_button_event_{{}}"
SIGNAL_VOLUME_EVENT = f"{DOMAIN}_volume_event_{{}}"

# Media content types for media browser
MEDIA_TYPE_PLAYLIST = "playlist"
MEDIA_TYPE_FIGURINE = "figurine"
MEDIA_TYPE_TRACK = "track"

# Version ids. Topic maps for these ids live in device_config.py.
# ``j1000`` and ``j2000`` match ``JookiDeviceConfig.version`` on the two tables.
DEVICE_VERSION_V1 = "j1000"
DEVICE_VERSION_V2 = "j2000"
DEVICE_VERSIONS = [DEVICE_VERSION_V1, DEVICE_VERSION_V2]

# Re-exported so existing imports keep working. Callers switch in a later commit.
__all__ = [
    "JookiDeviceConfig",
    "get_device_config",
]
