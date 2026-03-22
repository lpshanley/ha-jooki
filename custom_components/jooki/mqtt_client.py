"""MQTT client manager for the Jooki integration."""

from __future__ import annotations

import json
import logging
from typing import Any

import paho.mqtt.client as mqtt

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DEVICE_VERSION_V2,
    SIGNAL_BUTTON_EVENT,
    SIGNAL_NFC_EVENT,
    SIGNAL_STATE_UPDATED,
    SIGNAL_VOLUME_EVENT,
    JookiDeviceConfig,
)
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
        self._signal_nfc = SIGNAL_NFC_EVENT.format(entry_id)
        self._signal_button = SIGNAL_BUTTON_EVENT.format(entry_id)
        self._signal_volume = SIGNAL_VOLUME_EVENT.format(entry_id)

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.reconnect_delay_set(min_delay=5, max_delay=120)

    @property
    def host(self) -> str:
        """Return the device host address."""
        return self._host

    @property
    def state(self) -> JookiState:
        """Return the current device state."""
        return self._state

    @property
    def device_config(self) -> JookiDeviceConfig:
        """Return the version-specific device configuration."""
        return self._device_config

    @property
    def is_v2(self) -> bool:
        """Return True if this is a v2 device."""
        return self._device_config.version == DEVICE_VERSION_V2

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

    async def async_resync(self) -> None:
        """Send CONNECT handshake + GET_STATE to request a full state dump."""
        cfg = self._device_config
        connect_payload = json.dumps({
            "jooki": {
                "live": self._host,
                "version": "ha-jooki",
                "label": self._host,
            }
        })
        await self.async_publish(cfg.topic_connect, connect_payload)
        await self.async_publish(cfg.topic_get_state, "{}")
        _LOGGER.debug("Resync requested for Jooki at %s", self._host)

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
        cfg = self._device_config

        # Subscribe to all topics we care about
        client.subscribe(cfg.topic_state)
        client.subscribe(cfg.topic_error)
        client.subscribe(cfg.topic_nfc_tag)
        client.subscribe(cfg.topic_nfc_tag_removed)
        client.subscribe(cfg.topic_gpio_next)
        client.subscribe(cfg.topic_gpio_prev)
        client.subscribe(cfg.topic_gpio_circle)
        client.subscribe(cfg.topic_gpio_vol_set)

        # Audio playback events
        client.subscribe(cfg.topic_audio_position)
        client.subscribe(cfg.topic_audio_playing)
        client.subscribe(cfg.topic_audio_paused)
        client.subscribe(cfg.topic_audio_stopped)
        client.subscribe(cfg.topic_audio_error)
        client.subscribe(cfg.topic_audio_ended)

        # Reset state for accumulation
        self._state = JookiState(available=True)
        self._dispatch_state()

        # Request full state dump
        self._send_connect_handshake()
        self._request_full_state()

    def _send_connect_handshake(self) -> None:
        """Send the CONNECT handshake (runs on paho thread)."""
        connect_payload = json.dumps({
            "jooki": {
                "live": self._host,
                "version": "ha-jooki",
                "label": self._host,
            }
        })
        self._client.publish(self._device_config.topic_connect, connect_payload)

    def _request_full_state(self) -> None:
        """Send GET_STATE to request a full state dump (runs on paho thread)."""
        self._client.publish(self._device_config.topic_get_state, "{}")

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
        self._dispatch_state()

    def _on_message(
        self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage
    ) -> None:
        """Handle incoming MQTT message — route by topic."""
        topic = msg.topic
        cfg = self._device_config

        if topic == cfg.topic_state:
            self._handle_state_message(msg)
        elif topic == cfg.topic_nfc_tag:
            self._handle_nfc_tag(msg)
        elif topic == cfg.topic_nfc_tag_removed:
            self._handle_nfc_tag_removed()
        elif topic in (cfg.topic_gpio_next, cfg.topic_gpio_prev, cfg.topic_gpio_circle):
            self._handle_gpio_button(topic, msg)
        elif topic == cfg.topic_gpio_vol_set:
            self._handle_gpio_vol_set(msg)
        elif topic in (
            cfg.topic_audio_position,
            cfg.topic_audio_playing,
            cfg.topic_audio_paused,
            cfg.topic_audio_stopped,
            cfg.topic_audio_error,
            cfg.topic_audio_ended,
        ):
            self._handle_audio_event(topic, msg)
        elif topic == cfg.topic_error:
            self._handle_error(msg)

    def _handle_state_message(self, msg: mqtt.MQTTMessage) -> None:
        """Handle a state update from /j/web/output/state."""
        try:
            payload = json.loads(msg.payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            _LOGGER.warning("Invalid JSON from Jooki: %s", msg.payload[:200])
            return

        if self.is_v2:
            self._state.merge_partial(payload)
        else:
            self._state = JookiState.from_json(payload)

        self._dispatch_state()

    def _handle_nfc_tag(self, msg: mqtt.MQTTMessage) -> None:
        """Handle NFC figurine placed event."""
        try:
            parts = msg.payload.decode().split(",")
            tag_id = parts[0] if len(parts) >= 1 else ""
            star_id = parts[1] if len(parts) >= 2 else ""
        except (UnicodeDecodeError, IndexError):
            _LOGGER.warning("Invalid NFC tag payload: %s", msg.payload[:100])
            return

        self._hass.loop.call_soon_threadsafe(
            async_dispatcher_send,
            self._hass,
            self._signal_nfc,
            "figurine_placed",
            {"tag_id": tag_id, "star_id": star_id},
        )

    def _handle_nfc_tag_removed(self) -> None:
        """Handle NFC figurine removed event."""
        self._hass.loop.call_soon_threadsafe(
            async_dispatcher_send,
            self._hass,
            self._signal_nfc,
            "figurine_removed",
            {},
        )

    def _handle_gpio_button(self, topic: str, msg: mqtt.MQTTMessage) -> None:
        """Handle a GPIO button press/release event."""
        cfg = self._device_config
        button_map = {
            cfg.topic_gpio_next: "next",
            cfg.topic_gpio_prev: "previous",
            cfg.topic_gpio_circle: "circle",
        }
        button_name = button_map.get(topic, "unknown")

        try:
            value = msg.payload.decode().strip()
            event_type = "pressed" if value == "1" else "released"
        except UnicodeDecodeError:
            return

        self._hass.loop.call_soon_threadsafe(
            async_dispatcher_send,
            self._hass,
            self._signal_button,
            button_name,
            event_type,
        )

    def _handle_gpio_vol_set(self, msg: mqtt.MQTTMessage) -> None:
        """Handle a physical volume knob change event."""
        try:
            payload = json.loads(msg.payload)
            vol = payload.get("vol", "0")
        except (json.JSONDecodeError, UnicodeDecodeError):
            _LOGGER.warning("Invalid vol_set payload: %s", msg.payload[:200])
            return

        self._hass.loop.call_soon_threadsafe(
            async_dispatcher_send,
            self._hass,
            self._signal_volume,
            str(vol),
        )

    def _handle_audio_event(self, topic: str, msg: mqtt.MQTTMessage) -> None:
        """Handle audio subsystem events for improved state tracking."""
        cfg = self._device_config

        if topic == cfg.topic_audio_position:
            try:
                payload = json.loads(msg.payload)
                pos = payload.get("pos")
                if pos is not None:
                    self._state.playback_info.position_ms = int(pos)
                    self._state._rebuild_facade()
                    self._dispatch_state()
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                _LOGGER.warning(
                    "Invalid audio position payload: %s", msg.payload[:200]
                )
            return

        if topic == cfg.topic_audio_playing:
            self._state.playback_info.state = "playing"
        elif topic == cfg.topic_audio_paused:
            self._state.playback_info.state = "paused"
        elif topic == cfg.topic_audio_stopped:
            self._state.playback_info.state = "idle"
        elif topic == cfg.topic_audio_ended:
            self._state.playback_info.state = "idle"
            self._state.playback_info.position_ms = None
        elif topic == cfg.topic_audio_error:
            try:
                payload = json.loads(msg.payload)
                _LOGGER.warning("Jooki audio error: %s", payload)
            except (json.JSONDecodeError, UnicodeDecodeError):
                _LOGGER.warning("Jooki audio error (unparseable payload)")
            return

        self._state._rebuild_facade()
        self._dispatch_state()

    def _handle_error(self, msg: mqtt.MQTTMessage) -> None:
        """Handle an error/info message from the device."""
        try:
            payload = json.loads(msg.payload)
            error_msg = payload.get("msg", "Unknown error")
            _LOGGER.info("Jooki device message: %s", error_msg)

            # Extract locale from "Locale switched" confirmation
            info = payload.get("info")
            if isinstance(info, dict) and "locale" in info:
                self._state.device.locale = info["locale"]
                self._dispatch_state()
        except (json.JSONDecodeError, UnicodeDecodeError):
            _LOGGER.warning("Invalid error payload from Jooki: %s", msg.payload[:200])

    def _dispatch_state(self) -> None:
        """Send a state update signal to the HA event loop."""
        self._hass.loop.call_soon_threadsafe(
            async_dispatcher_send, self._hass, self._signal
        )
