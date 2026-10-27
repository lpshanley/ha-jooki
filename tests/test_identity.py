"""Jooki hostname, model, and DHCP MAC suffix checks."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("jooki-ab12", "jooki-ab12"),
        ("JOOKI-AB12", "jooki-ab12"),
        ("jooki-ab12.local", "jooki-ab12"),
        ("jooki-AB12.LOCAL", "jooki-ab12"),
        ("jooki2-041290", "jooki2-041290"),
        ("jooki2-041290.local", "jooki2-041290"),
        ("Jooki2-041290.Local", "jooki2-041290"),
        ("dev1", None),
        ("jooki", None),
        ("jooki-abc", None),
        ("jooki-abcde", None),
        ("jooki2-04129", None),
        ("jooki2-0412901", None),
        ("jooki-ab1g", None),
        ("jooki2-04129g", None),
        ("jooki-ab12.lan", None),
        ("jooki-ab12.local.local", None),
        ("prefix-jooki-ab12", None),
        ("jooki-ab12 ", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_hostname(identity, raw, expected):
    """Only a bare Jooki id, with an optional .local, is accepted."""
    assert identity.normalize_hostname(raw) == expected


def test_device_id_is_read_before_hostname(identity):
    """A valid device id wins. An invalid one falls through to hostname."""
    assert (
        identity.normalize_device_identity("jooki2-041290", "jooki-ab12")
        == "jooki2-041290"
    )
    assert identity.normalize_device_identity("dev1", "jooki-ab12.local") == "jooki-ab12"
    assert identity.normalize_device_identity("dev1", "jooki") is None
    assert identity.normalize_device_identity(None, None) is None
    assert identity.normalize_device_identity("", "jooki2-041290") == "jooki2-041290"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("jooki2-041290", "j2000"),
        ("jooki2-041290.local", "j2000"),
        ("jooki-ab12", "j1000"),
        ("JOOKI-AB12.local", "j1000"),
        ("dev1", None),
        ("jooki", None),
        (None, None),
    ],
)
def test_device_version_for_hostname(identity, raw, expected):
    """jooki2- is a J2000. A plain jooki- id is a J1000."""
    assert identity.device_version_for_hostname(raw) == expected


def test_mac_suffix_matches_j1000_tail_and_j2000_tail(identity):
    """J1000 uses the last 4 MAC hex digits. J2000 uses the last 6."""
    mac = "a8:ee:c6:04:12:90"
    assert identity.hostname_matches_mac("jooki2-041290", mac)
    assert identity.hostname_matches_mac("jooki2-041290.local", "A8EEC6041290")
    assert identity.hostname_matches_mac("jooki2-041290", "A8-EE-C6-04-12-90")
    assert identity.hostname_matches_mac("jooki2-041290", "a8ee.c604.1290")
    assert identity.hostname_matches_mac("jooki-1290", mac)
    assert not identity.hostname_matches_mac("jooki-0412", mac)
    assert not identity.hostname_matches_mac("jooki2-ffffff", mac)
    assert not identity.hostname_matches_mac("dev1", mac)
    assert not identity.hostname_matches_mac("jooki2-041290", None)
    assert not identity.hostname_matches_mac(None, mac)
    assert not identity.hostname_matches_mac("jooki2-041290", "not-a-mac")


def test_j2000_suffix_is_not_the_j1000_tail(identity):
    """A J2000 id matches the last six hex digits of the MAC."""
    mac = "aa:bb:cc:11:12:90"
    assert identity.hostname_matches_mac("jooki2-111290", mac)
    assert identity.hostname_matches_mac("jooki-1290", mac)
    assert not identity.hostname_matches_mac("jooki2-041290", mac)
    assert not identity.hostname_matches_mac("jooki-1112", mac)
