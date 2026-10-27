"""Local GStreamer events stay in raw state across later slices."""

from __future__ import annotations

import pytest


def test_position_event_survives_later_wifi_slice(models):
    """A position update must still be there after an unrelated slice."""
    state = models.JookiState()
    state.apply_slices(
        {
            "audio": {
                "playback": {"state": "PLAYING", "position_ms": 0},
                "nowPlaying": {"track": "Song"},
            },
            "wifi": {"ssid": "old"},
        }
    )

    assert state.apply_gstreamer_audio("position", {"id": 7, "pos": 15000})
    assert state.playback_info.position_ms == 15000
    assert state.raw["audio"]["playback"]["position_ms"] == 15000

    state.apply_slices({"wifi": {"ssid": "new", "signal": -50}})

    assert state.playback_info.position_ms == 15000
    assert state.playback.position_ms == 15000
    assert state.playback_info.state == "playing"
    assert state.now_playing.track == "Song"
    assert state.wifi.ssid == "new"
    assert state.wifi.signal == -50


@pytest.mark.parametrize("event", ["playing", "paused", "stopped", "ended"])
def test_gstreamer_transport_sets_playback_state(models, event):
    """playing/paused/stopped/ended are stored on the playback slice."""
    state = models.JookiState()
    state.apply_slices(
        {"audio": {"playback": {"state": "idle", "position_ms": 10}}}
    )

    assert state.apply_gstreamer_audio(event)
    assert state.playback_info.state == event
    assert state.raw["audio"]["playback"]["state"] == event
    if event == "ended":
        assert state.playback_info.position_ms is None
    else:
        assert state.playback_info.position_ms == 10
