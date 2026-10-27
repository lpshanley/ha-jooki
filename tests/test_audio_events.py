"""Local GStreamer events stay in raw state across later slices."""

from __future__ import annotations

import pytest


def test_unchanged_position_returns_none(models):
    """The same integer position does not rebuild or replace the catalog."""
    state = models.JookiState()
    state.apply_slices(
        {
            "db": {"playlists": {"pl1": {"title": "Dragons"}}},
            "audio": {"playback": {"state": "PLAYING", "position_ms": 15000}},
        }
    )
    db = state.db
    playback_info = state.playback_info
    playback = state.playback

    assert state.apply_gstreamer_audio("position", {"id": 7, "pos": 15000}) is None

    assert state.db is db
    assert state.playback_info is playback_info
    assert state.playback is playback
    assert state.playback_info.position_ms == 15000
    assert state.playback.position_ms == 15000
    assert state.raw["audio"]["playback"]["position_ms"] == 15000


def test_position_event_survives_later_wifi_slice(models):
    """A position update must still be there after an unrelated slice."""
    state = models.JookiState()
    state.apply_slices(
        {
            "db": {"playlists": {"pl1": {"title": "Dragons"}}},
            "audio": {
                "playback": {"state": "PLAYING", "position_ms": 0},
                "nowPlaying": {"track": "Song"},
            },
            "wifi": {"ssid": "old"},
        }
    )
    db = state.db
    playback_info = state.playback_info
    playback = state.playback

    assert (
        state.apply_gstreamer_audio("position", {"id": 7, "pos": 15000})
        == "position"
    )
    assert state.db is db
    assert state.playback_info is playback_info
    assert state.playback is playback
    assert state.playback_info.position_ms == 15000
    assert state.playback.position_ms == 15000
    assert state.raw["audio"]["playback"]["position_ms"] == 15000

    state.apply_slices({"wifi": {"ssid": "new", "signal": -50}})

    assert state.db is db
    assert state.playback_info.position_ms == 15000
    assert state.playback.position_ms == 15000
    assert state.playback_info.state == "playing"
    assert state.now_playing.track == "Song"
    assert state.wifi.ssid == "new"
    assert state.wifi.signal == -50
    assert state.db.playlists["pl1"].title == "Dragons"


@pytest.mark.parametrize("event", ["playing", "paused", "stopped", "ended"])
def test_gstreamer_transport_sets_playback_state(models, event):
    """playing/paused/stopped/ended are stored on the playback slice."""
    state = models.JookiState()
    state.apply_slices(
        {
            "db": {"playlists": {"pl1": {"title": "Dragons"}}},
            "audio": {"playback": {"state": "idle", "position_ms": 10}},
        }
    )
    db = state.db

    assert state.apply_gstreamer_audio(event) == "transport"
    assert state.db is db
    assert state.playback_info.state == event
    assert state.playback.state == event
    assert state.raw["audio"]["playback"]["state"] == event
    assert state.db.playlists["pl1"].title == "Dragons"
    if event == "ended":
        assert state.playback_info.position_ms is None
        assert state.playback.position_ms is None
    else:
        assert state.playback_info.position_ms == 10


@pytest.mark.parametrize(
    ("event", "payload"),
    [
        ("position", None),
        ("position", {}),
        ("position", {"id": 1}),
        ("position", {"pos": "nope"}),
        ("buffering", None),
    ],
)
def test_invalid_gstreamer_event_returns_none(models, event, payload):
    """Invalid audio events do not rebuild or invent a playback slice."""
    state = models.JookiState()
    db = state.db

    assert state.apply_gstreamer_audio(event, payload) is None

    assert state.db is db
    assert "audio" not in state.raw
