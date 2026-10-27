"""Figurine playback resolves a playlist before spoofing NFC."""

from __future__ import annotations


def test_jooki_dragon_is_rejected_as_wire_payload(models):
    """Star names are not hex codes, so firmware would drop the tag message."""
    assert models.nfc_tag_payload("04E8A76AE74C80", "Jooki.Dragon") is None
    assert models.nfc_tag_payload("04E8A76AE74C80", "211") == "04E8A76AE74C80,211"


def test_star_only_playlist_resolves_to_playlist_id(models):
    """A playlist linked by star and not tagId still plays by that star."""
    state = models.JookiState()
    state.apply_slices(
        {
            "db": {
                "playlists": {
                    "user_1": {"title": "Dragons", "star": "Jooki.Dragon"},
                }
            }
        }
    )

    playlist = state.db.playlists["user_1"]
    assert playlist.tag_id is None
    assert playlist.star == "Jooki.Dragon"
    assert (
        models.playlist_id_for_figurine(state.db.playlists, "Jooki.Dragon")
        == "user_1"
    )
