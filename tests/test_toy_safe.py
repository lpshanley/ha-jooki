"""Commanded Toy Safe survives device slices that omit the key."""

from __future__ import annotations


def test_note_toy_safe_survives_omitted_key_until_explicit_false(models):
    """A later device slice keeps Toy Safe unless it sends false."""
    state = models.JookiState()
    state.apply_slices(
        {
            "device": {
                "firmware": "1.2.3",
                "id": "dev1",
                "hostname": "jooki",
            }
        }
    )

    state.note_toy_safe(True)

    assert state.device.toy_safe is True
    assert state.device.firmware == "1.2.3"
    assert state.device.device_id == "dev1"
    assert state.device.hostname == "jooki"
    assert state.raw["device"]["toy_safe"] is True
    assert state.raw["device"]["firmware"] == "1.2.3"

    state.apply_slices({"device": {"firmware": "1.2.4", "id": "dev1"}})

    assert state.device.toy_safe is True
    assert state.device.firmware == "1.2.4"
    assert state.device.device_id == "dev1"
    assert state.device.hostname is None
    assert "toy_safe" not in state.raw["device"]

    state.apply_slices({"device": {"firmware": "1.2.4", "toy_safe": False}})

    assert state.device.toy_safe is False
    assert state.raw["device"]["toy_safe"] is False
    assert state.device.firmware == "1.2.4"

    state.apply_slices({"device": {"firmware": "9"}})

    assert state.device.toy_safe is False
    assert state.device.firmware == "9"


def test_non_dict_device_slice_keeps_commanded_toy_safe(models):
    """An empty device table keeps Toy Safe and resets other device fields."""
    state = models.JookiState()
    state.device.firmware = "keep-me"
    state.note_toy_safe(True)

    assert state.raw["device"] == {"toy_safe": True}
    assert state.device.toy_safe is True
    assert state.device.firmware == "keep-me"

    state.apply_slices(
        {"device": {"firmware": "1.0", "id": "abc", "toy_safe": True}}
    )
    state.apply_slices({"device": []})

    assert state.raw["device"] == []
    assert state.device.toy_safe is True
    assert state.device.firmware is None
    assert state.device.device_id is None
