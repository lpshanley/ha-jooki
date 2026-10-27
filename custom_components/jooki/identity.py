"""Hostname identity for a Jooki player.

This module does not import Home Assistant. ``const`` does, and the unit
tests load this file by path. Version ids match ``const.DEVICE_VERSION_V1``
and ``const.DEVICE_VERSION_V2`` (``j1000`` and ``j2000``).
"""

from __future__ import annotations

import re

_VERSION_J1000 = "j1000"
_VERSION_J2000 = "j2000"

_LOCAL_SUFFIX = ".local"
_HEX = frozenset("0123456789abcdef")
_JOOKI2 = re.compile(r"^jooki2-([0-9a-f]{6})$")
_JOOKI = re.compile(r"^jooki-([0-9a-f]{4})$")


def normalize_hostname(hostname: str | None) -> str | None:
    """Return ``jooki-`` plus 4 hex digits, or ``jooki2-`` plus 6.

    A trailing ``.local`` is removed. Any other name, including test values
    such as ``dev1``, is not a Jooki id.
    """
    if not isinstance(hostname, str):
        return None
    name = hostname
    if name.lower().endswith(_LOCAL_SUFFIX):
        name = name[: -len(_LOCAL_SUFFIX)]
    name = name.lower()
    if _JOOKI2.fullmatch(name) or _JOOKI.fullmatch(name):
        return name
    return None


def device_version_for_hostname(hostname: str | None) -> str | None:
    """Return ``j2000`` for ``jooki2-`` and ``j1000`` for ``jooki-``.

    ``jooki2-`` is checked first.
    """
    normalized = normalize_hostname(hostname)
    if normalized is None:
        return None
    if normalized.startswith("jooki2-"):
        return _VERSION_J2000
    if normalized.startswith("jooki-"):
        return _VERSION_J1000
    return None


def hostname_matches_mac(hostname: str | None, mac: str | None) -> bool:
    """Return True when the id suffix is the tail of a DHCP MAC.

    J1000 uses the last 4 hex digits. J2000 uses the last 6. Callers use
    this only when a DHCP MAC is in hand, so a stale lease whose address
    now belongs to something else is dropped.
    """
    normalized = normalize_hostname(hostname)
    if normalized is None or not isinstance(mac, str):
        return False
    hex_mac = _mac_hex(mac)
    if hex_mac is None:
        return False
    suffix = normalized.split("-", 1)[1]
    tail = 6 if normalized.startswith("jooki2-") else 4
    return len(hex_mac) >= tail and hex_mac.endswith(suffix)


def _mac_hex(mac: str) -> str | None:
    """Return lowercase hex digits from a MAC, or None."""
    cleaned = mac.replace(":", "").replace("-", "").replace(".", "").lower()
    if not cleaned or any(ch not in _HEX for ch in cleaned):
        return None
    return cleaned
