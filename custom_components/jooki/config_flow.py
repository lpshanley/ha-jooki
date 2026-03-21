"""Config flow for Jooki integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT

from .const import (
    CONF_DEVICE_VERSION,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEVICE_VERSION_V1,
    DEVICE_VERSION_V2,
    DEVICE_VERSIONS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_DEVICE_VERSION, default=DEVICE_VERSION_V1): vol.In(
            {
                DEVICE_VERSION_V1: "Jooki J1000 (Original)",
                DEVICE_VERSION_V2: "Jooki J2000 (Second Generation)",
            }
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


class JookiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jooki."""

    VERSION = 1

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
