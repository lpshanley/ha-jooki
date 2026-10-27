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


def test_figurine_label_prefers_token_name_then_playlist_then_star(models):
    """A parent-facing name is the token, else the tag's playlist, else the star."""
    state = models.JookiState()
    state.apply_slices(
        {
            "db": {
                "tokens": {
                    "TAG1": {"name": "Dragon", "starId": "Jooki.Dragon"},
                    "TAG2": {"name": "", "starId": "Jooki.Fox"},
                },
                "playlists": {
                    "p1": {"title": "Dragon Tales", "tagId": "TAG1"},
                    "p2": {"title": "Fox Stories", "tagId": "TAG2"},
                    "p3": {"title": "Unbound", "star": "Jooki.Owl"},
                },
            }
        }
    )

    assert models.figurine_label(state, "TAG1", "Jooki.Dragon") == "Dragon"
    assert models.figurine_label(state, "TAG2", "Jooki.Fox") == "Fox Stories"
    assert models.figurine_label(state, "MISSING", "Jooki.Owl") == "Jooki.Owl"
    assert models.figurine_label(state, None, None) is None
    assert models.figurine_label(state, "MISSING", "") is None
