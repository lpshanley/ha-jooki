"""MQTT client manager for the Jooki integration."""

from __future__ import annotations

import json
import logging
from typing import Any

import paho.mqtt.client as mqtt

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import JookiDeviceConfig, SIGNAL_STATE_UPDATED
from .models import JookiState

_LOGGER = logging.getLogger(__name__)


class JookiMqttClient:
    """Manage the MQTT connection to a Jooki device."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        entry_id: str,
        device_config: JookiDeviceConfig,
    ) -> None:
        """Initialize the MQTT client."""
        self._hass = hass
        self._host = host
        self._port = port
        self._entry_id = entry_id
        self._device_config = device_config
        self._state = JookiState()
        self._signal = SIGNAL_STATE_UPDATED.format(entry_id)

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.reconnect_delay_set(min_delay=5, max_delay=120)

    @property
    def state(self) -> JookiState:
        """Return the current device state."""
        return self._state

    @property
    def device_config(self) -> JookiDeviceConfig:
        """Return the version-specific device configuration."""
        return self._device_config

    async def async_start(self) -> None:
        """Start the MQTT client connection."""
        await self._hass.async_add_executor_job(self._start)

    def _start(self) -> None:
        """Connect and start the network loop (runs in executor)."""
        self._client.connect_async(self._host, self._port, keepalive=60)
        self._client.loop_start()

    async def async_stop(self) -> None:
        """Stop the MQTT client connection."""
        await self._hass.async_add_executor_job(self._stop)

    def _stop(self) -> None:
        """Disconnect and stop the network loop (runs in executor)."""
        self._client.loop_stop()
        self._client.disconnect()

    async def async_publish(self, topic: str, payload: str = "") -> None:
        """Publish a message to the Jooki."""
        await self._hass.async_add_executor_job(self._client.publish, topic, payload)

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Any,
        rc: int,
        properties: Any = None,
    ) -> None:
        """Handle MQTT connection established."""
        if rc != 0:
            _LOGGER.error("Failed to connect to Jooki MQTT broker: rc=%s", rc)
            return

        _LOGGER.debug("Connected to Jooki at %s:%s", self._host, self._port)
        client.subscribe(self._device_config.topic_state)
        self._state = JookiState(available=True)
        self._dispatch()

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Any,
        rc: int,
        properties: Any = None,
    ) -> None:
        """Handle MQTT disconnection."""
        _LOGGER.debug(
            "Disconnected from Jooki at %s:%s (rc=%s)", self._host, self._port, rc
        )
        self._state = JookiState(available=False)
        self._dispatch()

    def _on_message(
        self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage
    ) -> None:
        """Handle incoming MQTT message."""
        try:
            payload = json.loads(msg.payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            _LOGGER.warning("Invalid JSON from Jooki: %s", msg.payload[:200])
            return

        self._state = JookiState.from_json(payload)
        self._dispatch()

    def _dispatch(self) -> None:
        """Send a state update signal to the HA event loop."""
        self._hass.loop.call_soon_threadsafe(
            async_dispatcher_send, self._hass, self._signal
        )
