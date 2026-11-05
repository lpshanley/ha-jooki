"""MQTT credentials survive discovery and can be updated in place."""

from __future__ import annotations

from types import MappingProxyType
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from custom_components.jooki import config_flow

pytestmark = pytest.mark.asyncio

HOSTNAME = "jooki2-123456"
OLD_HOST = "192.0.2.10"
NEW_HOST = "192.0.2.20"


@pytest_asyncio.fixture
async def hass(tmp_path, monkeypatch):
    """Use real config-entry helpers without starting the integration platforms."""
    hass = HomeAssistant(str(tmp_path))
    hass.config_entries = ConfigEntries(hass, {})
    monkeypatch.setattr(hass.config_entries, "_async_schedule_save", Mock())
    monkeypatch.setattr(hass.config_entries, "async_schedule_reload", Mock())
    yield hass
    await hass.async_stop()


@pytest.fixture
def add_entry(hass):
    """Register an existing player without connecting to a real device."""

    def add(*, unique_id=HOSTNAME, authenticated=True, port=1883):
        data = {
            "host": OLD_HOST,
            "port": port,
            "name": "Bedroom Jooki",
            "device_version": "j2000",
        }
        if authenticated:
            data.update(username="jooki", password="old-password")
        entry = ConfigEntry(
            domain="jooki",
            title="Bedroom Jooki",
            unique_id=unique_id,
            version=1,
            minor_version=1,
            options={},
            source="user",
            data=data,
            discovery_keys=MappingProxyType({}),
            subentries_data=[],
            state=ConfigEntryState.LOADED,
        )
        hass.config_entries._entries[entry.entry_id] = entry
        return entry

    return add


@pytest.fixture
def mqtt_probe(monkeypatch):
    """Mock only device I/O; run the actual Home Assistant config-flow methods."""
    probe = Mock(return_value=None)
    monkeypatch.setattr(config_flow, "_test_mqtt_connection", probe)
    monkeypatch.setattr(
        config_flow,
        "_async_fetch_ping",
        AsyncMock(return_value={"hostname": HOSTNAME, "version": "1"}),
    )
    return probe


def make_flow(hass, source, entry=None):
    flow = config_flow.JookiConfigFlow()
    flow.hass = hass
    flow.handler = "jooki"
    flow.flow_id = "test-flow"
    flow.context = {"source": source}
    if entry is not None:
        flow.context["entry_id"] = entry.entry_id
    return flow


def discovery(ip=NEW_HOST):
    return DhcpServiceInfo(ip=ip, hostname=HOSTNAME, macaddress="A8EEC6123456")


async def test_dhcp_reuses_saved_credentials_and_port(hass, add_entry, mqtt_probe):
    entry = add_entry(port=1884)
    flow = make_flow(hass, "dhcp")

    with pytest.raises(AbortFlow) as result:
        await flow.async_step_dhcp(discovery())

    assert result.value.reason == "already_configured"
    mqtt_probe.assert_called_once_with(NEW_HOST, 1884, "jooki", "old-password")
    assert entry.data["host"] == NEW_HOST
    assert entry.data["password"] == "old-password"
    assert entry.unique_id == HOSTNAME
    hass.config_entries.async_schedule_reload.assert_called_once_with(entry.entry_id)


async def test_dhcp_adopts_authenticated_ip_keyed_entry(hass, add_entry, mqtt_probe):
    entry = add_entry(unique_id=OLD_HOST)
    flow = make_flow(hass, "dhcp")

    result = await flow.async_step_dhcp(discovery(OLD_HOST))

    assert result["reason"] == "already_configured"
    mqtt_probe.assert_called_once_with(OLD_HOST, 1883, "jooki", "old-password")
    assert entry.unique_id == HOSTNAME
    assert entry.data["password"] == "old-password"
    hass.config_entries.async_schedule_reload.assert_not_called()


async def test_dhcp_updates_stock_player_without_credentials(hass, add_entry, mqtt_probe):
    entry = add_entry(authenticated=False)
    flow = make_flow(hass, "dhcp")

    with pytest.raises(AbortFlow) as result:
        await flow.async_step_dhcp(discovery())

    assert result.value.reason == "already_configured"
    mqtt_probe.assert_called_once_with(NEW_HOST, 1883, None, None)
    assert entry.data["host"] == NEW_HOST
    hass.config_entries.async_schedule_reload.assert_called_once_with(entry.entry_id)


async def test_dhcp_rejected_login_does_not_update_entry(hass, add_entry, mqtt_probe):
    entry = add_entry()
    original = dict(entry.data)
    mqtt_probe.return_value = "invalid_auth"

    result = await make_flow(hass, "dhcp").async_step_dhcp(discovery())

    assert result["reason"] == "invalid_auth"
    assert dict(entry.data) == original
    hass.config_entries.async_schedule_reload.assert_not_called()


@pytest.mark.parametrize("error", [None, "invalid_auth"])
async def test_dhcp_new_device_still_probes_anonymously(hass, mqtt_probe, error):
    mqtt_probe.return_value = error

    result = await make_flow(hass, "dhcp").async_step_dhcp(discovery())

    mqtt_probe.assert_called_once_with(NEW_HOST, 1883, None, None)
    if error is None:
        assert result["type"] == "form"
        assert result["step_id"] == "discovery_confirm"
    else:
        assert result["reason"] == "invalid_auth"


async def test_reconfigure_suggests_saved_credentials(hass, add_entry, mqtt_probe):
    entry = add_entry()

    result = await make_flow(hass, "reconfigure", entry).async_step_reconfigure()

    assert result["type"] == "form"
    assert result["step_id"] == "reconfigure"
    suggestions = {
        key.schema: key.description["suggested_value"]
        for key in result["data_schema"].schema
    }
    assert suggestions == {"username": "jooki", "password": "old-password"}
    mqtt_probe.assert_not_called()


@pytest.mark.parametrize("authenticated", [True, False])
async def test_reconfigure_updates_existing_entry(
    hass, add_entry, mqtt_probe, authenticated
):
    entry = add_entry(authenticated=authenticated)
    original = dict(entry.data)
    credentials = {"username": "new-user", "password": "new-password"}

    result = await make_flow(hass, "reconfigure", entry).async_step_reconfigure(credentials)

    assert result["reason"] == "reconfigure_successful"
    mqtt_probe.assert_called_once_with(OLD_HOST, 1883, "new-user", "new-password")
    assert dict(entry.data) == {**original, **credentials}
    assert entry.unique_id == HOSTNAME
    assert entry.title == "Bedroom Jooki"
    assert hass.config_entries.async_entries("jooki") == [entry]
    hass.config_entries.async_schedule_reload.assert_called_once_with(entry.entry_id)


@pytest.mark.parametrize("error", ["invalid_auth", "cannot_connect"])
async def test_reconfigure_failure_preserves_entry(hass, add_entry, mqtt_probe, error):
    entry = add_entry()
    original = dict(entry.data)
    credentials = {"username": "new-user", "password": "incorrect"}
    mqtt_probe.return_value = error

    result = await make_flow(hass, "reconfigure", entry).async_step_reconfigure(credentials)

    assert result["type"] == "form"
    assert result["errors"] == {"base": error}
    assert dict(entry.data) == original
    suggestions = {
        key.schema: key.description["suggested_value"]
        for key in result["data_schema"].schema
    }
    assert suggestions == credentials
    hass.config_entries.async_schedule_reload.assert_not_called()


@pytest.mark.parametrize("credentials", [{}, {"username": "", "password": ""}])
async def test_reconfigure_can_clear_credentials(hass, add_entry, mqtt_probe, credentials):
    entry = add_entry()
    original = dict(entry.data)

    result = await make_flow(hass, "reconfigure", entry).async_step_reconfigure(credentials)

    assert result["reason"] == "reconfigure_successful"
    mqtt_probe.assert_called_once_with(
        OLD_HOST, 1883, credentials.get("username"), credentials.get("password")
    )
    assert not entry.data.get("username")
    assert not entry.data.get("password")
    for key in ("host", "port", "name", "device_version"):
        assert entry.data[key] == original[key]
    hass.config_entries.async_schedule_reload.assert_called_once_with(entry.entry_id)


async def test_failed_credential_clear_does_not_restore_suggestions(
    hass, add_entry, mqtt_probe
):
    entry = add_entry()
    mqtt_probe.return_value = "invalid_auth"

    result = await make_flow(hass, "reconfigure", entry).async_step_reconfigure({})

    assert result["errors"] == {"base": "invalid_auth"}
    assert all(not key.description for key in result["data_schema"].schema)
    assert entry.data["password"] == "old-password"
    hass.config_entries.async_schedule_reload.assert_not_called()
