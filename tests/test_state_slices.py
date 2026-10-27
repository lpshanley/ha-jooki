"""Partial MQTT state replaces a slice and leaves sibling slices alone."""

from __future__ import annotations


def test_playback_slice_keeps_playlists_battery_and_now_playing(models):
    """A later playback slice must not wipe slices from GET_STATE."""
    state = models.JookiState()
    state.apply_slices(
        {
            "db": {
                "playlists": {
                    "pl1": {"title": "Dragons", "tracks": ["t1"]},
                }
            },
            "power": {
                "charging": False,
                "connected": True,
                "level": {"p": 845, "mv": 3800},
            },
            "audio": {
                "config": {"volume": 40, "repeat_mode": 1},
                "nowPlaying": {
                    "track": "Song",
                    "album": "Album",
                    "artist": "A",
                },
                "playback": {"state": "PLAYING", "position_ms": 1000},
            },
        }
    )

    state.apply_slices(
        {"audio": {"playback": {"state": "PAUSED", "position_ms": 2000}}}
    )

    assert state.db.playlists["pl1"].title == "Dragons"
    assert state.db.playlists["pl1"].tracks == ["t1"]
    assert state.power.battery_percent == 84.5
    assert state.power.battery_mv == 3800
    assert state.now_playing.track == "Song"
    assert state.now_playing.album == "Album"
    assert state.audio_config.volume == 40
    assert state.playback_info.state == "paused"
    assert state.playback_info.position_ms == 2000
    assert state.playback.state == "paused"
    assert state.playback.track == "Song"


def test_replaced_now_playing_omitting_album_drops_it(models):
    """A nowPlaying slice is replaced, so a missing album is not kept."""
    state = models.JookiState()
    state.apply_slices(
        {
            "audio": {
                "nowPlaying": {
                    "track": "Song",
                    "album": "Old",
                    "artist": "A",
                    "image": "/artwork/old.jpg",
                }
            }
        }
    )

    state.apply_slices(
        {"audio": {"nowPlaying": {"track": "Other", "artist": "B"}}}
    )

    assert state.now_playing.track == "Other"
    assert state.now_playing.artist == "B"
    assert state.now_playing.album is None
    assert state.now_playing.image is None
    assert state.playback.album is None


def test_db_slice_omitting_playlist_deletes_it(models):
    """A db slice replaces the catalog, so a missing playlist id is deleted."""
    state = models.JookiState()
    state.apply_slices(
        {
            "db": {
                "playlists": {
                    "keep": {"title": "Keep"},
                    "drop": {"title": "Drop"},
                },
                "tokens": {"abc": {"name": "Dragon", "starId": "Jooki.Dragon"}},
            }
        }
    )

    state.apply_slices({"db": {"playlists": {"keep": {"title": "Kept"}}}})

    assert set(state.db.playlists) == {"keep"}
    assert state.db.playlists["keep"].title == "Kept"
    assert state.db.tokens == {}


def test_empty_nfc_list_clears_figurine(models):
    """``nfc: []`` is an empty Lua table and means the reader is empty."""
    state = models.JookiState()
    state.apply_slices(
        {
            "nfc": {"starId": "Jooki.Dragon", "tagId": "04E8A76AE74C80"},
            "db": {"playlists": {"p": {"title": "Dragons"}}},
        }
    )
    assert state.nfc.present is True
    assert state.nfc.star_id == "Jooki.Dragon"

    state.apply_slices({"nfc": []})

    assert state.nfc.present is False
    assert state.nfc.star_id is None
    assert state.nfc.tag_id is None
    assert "p" in state.db.playlists


def test_mapped_device_wifi_and_catalog_fields(models):
    """Disk usage, wifi, and playlist/token/track rows keep their mapping."""
    state = models.JookiState()
    state.apply_slices(
        {
            "device": {"id": "dev1", "diskUsage": {"usedPercent": 42}},
            "wifi": {
                "ssid": "net",
                "bssid": "aa:bb",
                "ch": 6,
                "signal": -40,
                "crypt": 3,
                "stat": "success",
            },
            "db": {
                "playlists": {
                    "p": {
                        "title": "T",
                        "tagId": "ABC",
                        "tracks": ["tr"],
                        "spotify": {"source": "Party", "uri": "spotify:playlist:1"},
                    }
                },
                "tokens": {"ABC": {"name": "Dragon", "starId": "Jooki.Dragon"}},
                "tracks": {
                    "tr": {
                        "title": "Song",
                        "duration": 12,
                        "format2": "ID3 tag",
                        "hasImage": True,
                    }
                },
            },
        }
    )

    assert state.device.disk_usage["usedPercent"] == 42
    assert state.device.device_id == "dev1"
    wifi = state.wifi
    assert (wifi.ssid, wifi.bssid, wifi.channel, wifi.signal, wifi.crypt, wifi.stat) == (
        "net",
        "aa:bb",
        6,
        -40,
        3,
        "success",
    )
    playlist = state.db.playlists["p"]
    assert playlist.tag_id == "ABC"
    assert playlist.tracks == ["tr"]
    assert playlist.spotify_uri == "spotify:playlist:1"
    assert state.db.tokens["ABC"].star_id == "Jooki.Dragon"
    assert state.db.tracks["tr"].format == "ID3 tag"
    assert state.db.tracks["tr"].duration == 12
    assert state.db.tracks["tr"].has_image is True
