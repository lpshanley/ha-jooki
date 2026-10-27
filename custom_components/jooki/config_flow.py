"""Config flow for Jooki integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from .const import (
    CONF_DEVICE_VERSION,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEVICE_VERSION_V1,
    DEVICE_VERSION_V2,
    DOMAIN,
)
from .identity import device_version_for_hostname, hostname_matches_mac, normalize_hostname

_LOGGER = logging.getLogger(__name__)

_PING_TIMEOUT = aiohttp.ClientTimeout(total=3)
_DEVICE_VERSIONS = {
    DEVICE_VERSION_V1: "Jooki J1000 (Original)",
    DEVICE_VERSION_V2: "Jooki J2000 (Second Generation)",
}

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_DEVICE_VERSION, default=DEVICE_VERSION_V1): vol.In(
            _DEVICE_VERSIONS
        ),
    }
)

STATE_TOPIC = "/j/web/output/state"


def _test_mqtt_connection(host: str, port: int) -> bool:
    """Test MQTT connection to a Jooki device (runs in executor)."""
    import time

    import paho.mqtt.client as mqtt

    connected = False

    def on_connect(client: mqtt.Client, userdata: Any, flags: Any, rc: int, properties: Any = None) -> None:
        nonlocal connected
        if rc == 0:
            connected = True
            client.disconnect()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect

    try:
        client.connect(host, port, keepalive=5)
        client.loop_start()
        deadline = time.monotonic() + 5
        while not connected and time.monotonic() < deadline:
            time.sleep(0.1)
        client.loop_stop()
        client.disconnect()
    except Exception:
        _LOGGER.debug("Failed to connect to MQTT broker at %s:%s", host, port)
        return False

    return connected


async def _async_fetch_ping(hass: HomeAssistant, host: str) -> dict[str, Any] | None:
    """GET /ping, or None when the player does not answer."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(f"http://{host}/ping", timeout=_PING_TIMEOUT) as response:
            if response.status != 200:
                return None
            payload = await response.json(content_type=None)
    except (TimeoutError, aiohttp.ClientError, ValueError):
        _LOGGER.debug("Jooki ping failed for %s", host)
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _ping_hostname(payload: object, mac: str | None = None) -> str | None:
    """Return a normalized hostname when ping has a version. Check ``mac`` when passed."""
    if not isinstance(payload, dict):
        return None
    version = payload.get("version")
    if isinstance(version, bool) or not isinstance(version, (str, int, float)) or version == "":
        return None
    hostname = normalize_hostname(payload.get("hostname"))
    if hostname is None:
        return None
    if mac is not None and not hostname_matches_mac(hostname, mac):
        return None
    return hostname


def _changed_host(
    hass: HomeAssistant, unique_id: str, host: str
) -> dict[str, str] | None:
    """Return a host update when this unique id is already on another address."""
    entry = hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, unique_id)
    if entry is None or entry.data.get(CONF_HOST) == host:
        return None
    return {CONF_HOST: host}


class JookiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jooki."""

    VERSION = 1
    _discovered: dict[str, str] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            can_connect = await self.hass.async_add_executor_job(
                _test_mqtt_connection, host, port
            )

            if can_connect:
                hostname = _ping_hostname(await _async_fetch_ping(self.hass, host))
                if hostname is not None:
                    await self.async_set_unique_id(hostname)
                    self._abort_if_unique_id_configured(
                        updates=_changed_host(self.hass, hostname, host)
                    )
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Confirm a MuuseLabs DHCP lease with /ping and MQTT."""
        ip = discovery_info.ip
        hostname = _ping_hostname(
            await _async_fetch_ping(self.hass, ip), discovery_info.macaddress
        )
        if hostname is None:
            return self.async_abort(reason="not_jooki")

        can_connect = await self.hass.async_add_executor_job(
            _test_mqtt_connection, ip, DEFAULT_PORT
        )
        if not can_connect:
            return self.async_abort(reason="cannot_connect")

        version = device_version_for_hostname(hostname)
        if version is None:
            return self.async_abort(reason="not_jooki")

        await self.async_set_unique_id(hostname)
        self._abort_if_unique_id_configured(
            updates=_changed_host(self.hass, hostname, ip)
        )
        adopted = self._adopt_ip_keyed_entry(ip, hostname)
        if adopted is not None:
            return adopted

        self._discovered = {
            CONF_HOST: ip,
            "hostname": hostname,
            CONF_DEVICE_VERSION: version,
        }
        return await self.async_step_discovery_confirm()

    def _adopt_ip_keyed_entry(self, ip: str, hostname: str) -> ConfigFlowResult | None:
        """Rewrite an entry still keyed by this IP, then abort."""
        entry = self.hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, ip)
        if entry is None:
            return None
        host_changed = entry.data.get(CONF_HOST) != ip
        self.hass.config_entries.async_update_entry(
            entry,
            unique_id=hostname,
            data={**entry.data, CONF_HOST: ip},
        )
        if host_changed and entry.state == ConfigEntryState.LOADED:
            self.hass.config_entries.async_schedule_reload(entry.entry_id)
        return self.async_abort(reason="already_configured")

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user to add a discovered player."""
        discovered = self._discovered
        if discovered is None:
            return self.async_abort(reason="not_jooki")

        hostname = discovered["hostname"]
        ip = discovered[CONF_HOST]
        version = discovered[CONF_DEVICE_VERSION]
        if user_input is not None:
            return self.async_create_entry(
                title=hostname,
                data={
                    CONF_HOST: ip,
                    CONF_PORT: DEFAULT_PORT,
                    CONF_NAME: hostname,
                    CONF_DEVICE_VERSION: version,
                },
            )

        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={
                "hostname": hostname,
                "model": _DEVICE_VERSIONS.get(version, version),
                "ip": ip,
            },
        )
