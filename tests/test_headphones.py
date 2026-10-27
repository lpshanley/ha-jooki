"""J2000 headphone jack updates audio.config inside raw state."""

from __future__ import annotations


def test_hp_plugged_sets_both_jack_values(models):
    """``1`` enables headphones and ``0`` clears them without dropping volume."""
    state = models.JookiState()
    state.apply_slices(
        {
            "audio": {
                "config": {
                    "volume": 30,
                    "headphones_en": False,
                    "repeat_mode": 1,
                }
            }
        }
    )

    assert state.apply_hp_plugged("nope") is False
    assert state.apply_hp_plugged("0") is False
    assert state.audio_config.headphones_en is False

    assert state.apply_hp_plugged("1") is True
    audio_config = state.audio_config
    assert state.apply_hp_plugged("1") is False
    assert state.audio_config is audio_config

    state.apply_slices({"wifi": {"ssid": "net"}})
    assert state.audio_config is audio_config
    assert state.audio_config.headphones_en is True
    assert state.raw["audio"]["config"]["headphones_en"] is True
    assert state.audio_config.volume == 30

    assert state.apply_hp_plugged("0") is True
    assert state.audio_config.headphones_en is False
    assert state.raw["audio"]["config"]["headphones_en"] is False
    assert state.audio_config.volume == 30
    assert state.apply_hp_plugged("0") is False
