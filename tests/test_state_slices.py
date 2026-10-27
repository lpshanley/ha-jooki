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


def test_battery_temperature_follows_the_power_slice(models):
    """``power.level.t`` is millidegrees C and is cleared when omitted.

    An audio slice does not rebuild power, so the reading stays. A later
    power slice that omits ``t`` drops it. Playlists are a different slice.
    """
    state = models.JookiState()
    state.apply_slices(
        {
            "db": {"playlists": {"pl1": {"title": "Dragons"}}},
            "power": {
                "charging": False,
                "connected": True,
                "level": {"p": 845, "mv": 3800, "t": 40000},
            },
        }
    )

    assert state.power.battery_c == 40.0
    assert state.db.playlists["pl1"].title == "Dragons"

    state.apply_slices({"audio": {"config": {"volume": 12}}})

    assert state.power.battery_c == 40.0
    assert state.audio_config.volume == 12

    state.apply_slices(
        {"power": {"charging": True, "level": {"p": 500, "mv": 3700}}}
    )

    assert state.power.battery_c is None
    assert state.power.battery_percent == 50.0
    assert state.power.charging is True
    assert state.db.playlists["pl1"].title == "Dragons"


def test_now_playing_omitting_restricted_stays_false(models):
    """A replaced nowPlaying slice that omits ``restricted`` is not explicit."""
    state = models.JookiState()
    state.apply_slices(
        {"audio": {"nowPlaying": {"track": "Song", "restricted": True}}}
    )

    assert state.now_playing.restricted is True

    state.apply_slices({"audio": {"nowPlaying": {"track": "Other"}}})

    assert state.now_playing.track == "Other"
    assert state.now_playing.restricted is False


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


def test_bluetooth_survives_wifi_and_replaces_on_its_own_key(models):
    """``bluetooth.connected_mac`` is its own slice. A non-dict clears it."""
    state = models.JookiState()
    state.apply_slices(
        {
            "bluetooth": {
                "connected_mac": "D4:5E:EC:75:2A:F4",
                "devices": {"20:74:CF:3C:B3:97": {"name": "Air"}},
            },
            "wifi": {"ssid": "old"},
        }
    )

    assert state.bluetooth.connected_mac == "D4:5E:EC:75:2A:F4"
    assert not hasattr(state.bluetooth, "devices")

    state.apply_slices({"wifi": {"ssid": "net"}})

    assert state.bluetooth.connected_mac == "D4:5E:EC:75:2A:F4"
    assert state.wifi.ssid == "net"

    state.apply_slices({"bluetooth": {"connected_mac": "AA:BB:CC:DD:EE:FF"}})

    assert state.bluetooth.connected_mac == "AA:BB:CC:DD:EE:FF"
    assert state.wifi.ssid == "net"

    state.apply_slices({"bluetooth": []})

    assert state.bluetooth.connected_mac is None
    assert state.wifi.ssid == "net"


def test_user_messages_survive_wifi_and_replace_on_their_own_key(models):
    """``userMessages`` is its own slice and unknown items are ignored."""
    state = models.JookiState()
    state.apply_slices(
        {
            "userMessages": [
                {
                    "id": 1,
                    "level": "ERROR",
                    "messageType": "disk.full",
                    "extra": {"detail_msg": "full"},
                },
                "nope",
                {"unexpected": True},
                {"id": 2, "level": "INFO", "messageType": "hello"},
            ],
            "wifi": {"ssid": "old"},
        }
    )

    assert [(m.id, m.level, m.message_type) for m in state.user_messages] == [
        (1, "ERROR", "disk.full"),
        (2, "INFO", "hello"),
    ]
    assert state.user_messages[0].extra == {"detail_msg": "full"}

    state.apply_slices({"wifi": {"ssid": "net"}})

    assert [m.id for m in state.user_messages] == [1, 2]
    assert state.wifi.ssid == "net"

    state.apply_slices(
        {"userMessages": [{"id": 3, "level": "INFO", "messageType": "newer"}]}
    )

    assert [m.message_type for m in state.user_messages] == ["newer"]
    assert state.wifi.ssid == "net"

    state.apply_slices({"userMessages": {}})

    assert state.user_messages == []
    assert state.wifi.ssid == "net"

    state.apply_slices(
        {"userMessages": [{"id": 4, "level": "INFO", "messageType": "again"}]}
    )
    state.apply_slices({"userMessages": []})

    assert state.user_messages == []


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
