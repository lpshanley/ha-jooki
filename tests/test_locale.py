"""A device slice that omits locale keeps the language the user selected."""

from __future__ import annotations


def test_missing_device_locale_keeps_selected_language(models):
    """Missing locale must not fall back to English over the user's choice."""
    assert models.retained_locale("fr", None) == "fr"
    assert models.retained_locale("de", "") == "de"
    assert models.retained_locale("en", "fr") == "fr"
