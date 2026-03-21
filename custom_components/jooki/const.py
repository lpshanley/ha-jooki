"""Constants for the Jooki integration."""

from homeassistant.const import Platform

DOMAIN = "jooki"
DEFAULT_PORT = 1883
DEFAULT_NAME = "Jooki"
MAX_VOLUME = 100

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.LIGHT,
    Platform.MEDIA_PLAYER,
    Platform.SENSOR,
]

# MQTT topics — state
TOPIC_STATE = "/j/web/output/state"

# MQTT topics — commands
TOPIC_SET_VOL = "/j/web/input/SET_VOL"
TOPIC_DO_PLAY = "/j/web/input/DO_PLAY"
TOPIC_DO_PAUSE = "/j/web/input/DO_PAUSE"
TOPIC_DO_NEXT = "/j/web/input/DO_NEXT"
TOPIC_DO_PREV = "/j/web/input/DO_PREV"
TOPIC_PLAYLIST_PLAY = "/j/web/input/PLAYLIST_PLAY"
TOPIC_SHUTDOWN = "/j/web/input/SHUTDOWN"

# MQTT topics — LEDs
TOPIC_LED_SET_RAW = "/j/led/output/set_raw"
TOPIC_LED_PULSE_RAW = "/j/led/output/pulse_raw"

# LED identifiers
LED_IDS = ["ALL", "CIRCLE", "NEXT", "VOL_INC", "VOL_DEC", "PREV", "RING"]

# Dispatcher signal (formatted with entry_id)
SIGNAL_STATE_UPDATED = f"{DOMAIN}_state_updated_{{}}"
