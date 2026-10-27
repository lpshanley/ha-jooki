"""Outbound command topics and payloads match the J1000 wire protocol."""

from __future__ import annotations

import pytest


def _topics(device_config):
    """J1000 command topics from ``device_config``, loaded without Home Assistant."""
    return device_config.get_device_config(device_config.DEVICE_CONFIG_V1.version)


@pytest.mark.parametrize(
    ("encode", "topic"),
    [
        ("play", "/j/web/input/DO_PLAY"),
        ("pause", "/j/web/input/DO_PAUSE"),
        ("next_track", "/j/web/input/DO_NEXT"),
        ("previous_track", "/j/web/input/DO_PREV"),
    ],
)
def test_transport_commands_publish_an_empty_object(device_commands, device_config, encode, topic):
    """Play, pause, next, and previous send ``{}``."""
    actual_topic, payload = getattr(device_commands, encode)(_topics(device_config))
    assert actual_topic == topic
    assert payload == "{}"


@pytest.mark.parametrize(
    ("position", "payload"),
    [
        (0.0, '{"position_ms": "0.0"}'),
        (1.5, '{"position_ms": "1500.0"}'),
        (10.0, '{"position_ms": "10000.0"}'),
    ],
)
def test_seek_sends_position_ms_as_a_string(device_commands, device_config, position, payload):
    """Seconds become ``str(position * 1000)``, including a float's decimal."""
    topic, actual = device_commands.seek(_topics(device_config), position)
    assert topic == "/j/web/input/SEEK"
    assert actual == payload


@pytest.mark.parametrize(
    ("volume", "payload"),
    [
        (0.0, '{"vol": "0"}'),
        (0.29, '{"vol": "28"}'),
        (0.5, '{"vol": "50"}'),
        (1.0, '{"vol": "100"}'),
    ],
)
def test_volume_is_scaled_to_a_string(device_commands, device_config, volume, payload):
    """0.0 to 1.0 is ``int(volume * scale)`` with scale 100 (``MAX_VOLUME``)."""
    topic, actual = device_commands.set_volume(_topics(device_config), volume, scale=100)
    assert topic == "/j/web/input/SET_VOL"
    assert actual == payload


@pytest.mark.parametrize("mode", [0, 1, 2])
def test_repeat_mode_is_the_device_integer(device_commands, device_config, mode):
    """Repeat publishes the Jooki integer, not a Home Assistant enum name."""
    topic, payload = device_commands.set_repeat_mode(_topics(device_config), mode)
    assert topic == "/j/web/input/SET_CFG"
    assert payload == f'{{"repeat_mode": {mode}}}'


@pytest.mark.parametrize(
    ("shuffle", "payload"),
    [
        (True, '{"shuffle_mode": true}'),
        (False, '{"shuffle_mode": false}'),
    ],
)
def test_shuffle_mode_is_a_json_bool(device_commands, device_config, shuffle, payload):
    """Shuffle uses SET_CFG and a JSON boolean."""
    topic, actual = device_commands.set_shuffle(_topics(device_config), shuffle)
    assert topic == "/j/web/input/SET_CFG"
    assert actual == payload


def test_shutdown_names_the_web_source(device_commands, device_config):
    """Shutdown sends ``src`` ``from-web``."""
    topic, payload = device_commands.shutdown(_topics(device_config))
    assert topic == "/j/web/input/SHUTDOWN"
    assert payload == '{"src": "from-web"}'


@pytest.mark.parametrize(
    ("track_index", "payload"),
    [
        (0, '{"playlistId": "user_1", "trackIndex": 0}'),
        (1, '{"playlistId": "user_1", "trackIndex": 1}'),
    ],
)
def test_play_playlist_keeps_the_track_index(device_commands, device_config, track_index, payload):
    """Playlist play does not adjust a 0-based or 1-based index."""
    topic, actual = device_commands.play_playlist(_topics(device_config), "user_1", track_index)
    assert topic == "/j/web/input/PLAYLIST_PLAY"
    assert actual == payload
