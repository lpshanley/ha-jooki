"""MQTT client manager for the Jooki integration."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

import paho.mqtt.client as mqtt

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from . import device_commands
from .device_commands import JookiDevice
from .const import (
    DEVICE_VERSION_V2,
    MAX_VOLUME,
    SIGNAL_BUTTON_EVENT,
    SIGNAL_NFC_EVENT,
    SIGNAL_POSITION_UPDATED,
    SIGNAL_STATE_UPDATED,
    SIGNAL_VOLUME_EVENT,
)
from .device_config import JookiDeviceConfig
from .models import JookiState, figurine_label

_LOGGER = logging.getLogger(__name__)


class JookiMqttClient(JookiDevice):
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
        self._signal_position = SIGNAL_POSITION_UPDATED.format(entry_id)
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
    def model_name(self) -> str:
        """Return the model name for this device family."""
        return self._device_config.model_name

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

    async def _async_publish(self, topic: str, payload: str = "") -> None:
        """Enqueue a publish.

        ``Client.publish`` only queues the message. The network loop sends it.
        """
        self._client.publish(topic, payload)

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
        await self._async_publish(cfg.topic_connect, connect_payload)
        await self._async_publish(cfg.topic_get_state, "{}")
        _LOGGER.debug("Resync requested for Jooki at %s", self._host)

    async def async_play(self) -> None:
        """Send play command."""
        topic, payload = device_commands.play(self._device_config)
        await self._async_publish(topic, payload)

    async def async_pause(self) -> None:
        """Send pause command."""
        topic, payload = device_commands.pause(self._device_config)
        await self._async_publish(topic, payload)

    async def async_next_track(self) -> None:
        """Send next track command."""
        topic, payload = device_commands.next_track(self._device_config)
        await self._async_publish(topic, payload)

    async def async_previous_track(self) -> None:
        """Send previous track command."""
        topic, payload = device_commands.previous_track(self._device_config)
        await self._async_publish(topic, payload)

    async def async_seek(self, position: float) -> None:
        """Seek to a position in the current track (seconds)."""
        topic, payload = device_commands.seek(self._device_config, position)
        await self._async_publish(topic, payload)

    async def async_set_volume(self, volume: float) -> None:
        """Set volume from a 0.0 to 1.0 level."""
        topic, payload = device_commands.set_volume(
            self._device_config, volume, scale=MAX_VOLUME
        )
        await self._async_publish(topic, payload)

    async def async_set_repeat_mode(self, mode: int) -> None:
        """Set repeat mode from the device value 0, 1, or 2."""
        topic, payload = device_commands.set_repeat_mode(self._device_config, mode)
        await self._async_publish(topic, payload)

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Set shuffle mode."""
        topic, payload = device_commands.set_shuffle(self._device_config, shuffle)
        await self._async_publish(topic, payload)

    async def async_shutdown(self) -> None:
        """Shut down the Jooki."""
        topic, payload = device_commands.shutdown(self._device_config)
        await self._async_publish(topic, payload)

    async def async_play_playlist(self, playlist_id: str, track_index: int) -> None:
        """Play a playlist from ``track_index``."""
        topic, payload = device_commands.play_playlist(
            self._device_config, playlist_id, track_index
        )
        await self._async_publish(topic, payload)

    async def async_send_nfc_tag(self, payload: str) -> None:
        """Send an NFC tag payload string unchanged."""
        topic, body = device_commands.nfc_tag(self._device_config, payload)
        await self._async_publish(topic, body)

    async def async_set_toy_safe(self, enable: bool) -> None:
        """Enable or disable Toy Safe mode."""
        topic, payload = device_commands.set_toy_safe(self._device_config, enable)
        await self._async_publish(topic, payload)
        self._state.note_toy_safe(enable)

    async def async_set_locale(self, locale_code: str) -> None:
        """Switch the device language."""
        topic, payload = device_commands.set_locale(self._device_config, locale_code)
        await self._async_publish(topic, payload)

    async def async_set_led_raw(self, r: int, g: int, b: int) -> None:
        """Set the LED ring to an RGB color."""
        topic, payload = device_commands.set_led_raw(self._device_config, r, g, b)
        await self._async_publish(topic, payload)

    async def async_pulse_led(self, payload: str) -> None:
        """Publish a pulse_raw wire string such as ``ALL,255,0,0,3,500,1.0``."""
        topic, body = device_commands.pulse_led(self._device_config, payload)
        await self._async_publish(topic, body)

    async def async_set_charge_effect(self, effect: str) -> None:
        """Publish a charge_state token such as ``BAT_INC`` or ``BAT_DEC``."""
        topic, payload = device_commands.set_charge_effect(self._device_config, effect)
        await self._async_publish(topic, payload)

    async def async_turn_off_led(self) -> None:
        """Turn the LED ring off."""
        topic, payload = device_commands.turn_off_led(self._device_config)
        await self._async_publish(topic, payload)

    async def async_skip_seconds(self, delta_s: int) -> None:
        """Skip forward or backward by ``delta_s`` seconds."""
        topic, payload = device_commands.skip_seconds(self._device_config, delta_s)
        await self._async_publish(topic, payload)

    def _schedule(self, callback: Callable[..., None], *args: Any) -> None:
        """Queue ``callback`` on the Home Assistant loop, in arrival order.

        ``RuntimeError`` means the loop is already closed during unload.
        """
        try:
            self._hass.loop.call_soon_threadsafe(callback, *args)
        except RuntimeError:
            return

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
        # Queue the reset before subscribe and the handshake. A fast
        # GET_STATE reply is then applied to the fresh state, not wiped by it.
        self._schedule(self._on_loop_connected)

        cfg = self._device_config
        client.subscribe(cfg.topic_state)
        client.subscribe(cfg.topic_error)
        client.subscribe(cfg.topic_nfc_tag)
        client.subscribe(cfg.topic_nfc_tag_removed)
        client.subscribe(cfg.topic_gpio_next)
        client.subscribe(cfg.topic_gpio_prev)
        client.subscribe(cfg.topic_gpio_circle)
        client.subscribe(cfg.topic_gpio_vol_set)
        client.subscribe(cfg.topic_audio_position)
        client.subscribe(cfg.topic_audio_playing)
        client.subscribe(cfg.topic_audio_paused)
        client.subscribe(cfg.topic_audio_stopped)
        client.subscribe(cfg.topic_audio_error)
        client.subscribe(cfg.topic_audio_ended)

        if self.is_v2 and cfg.topic_gpio_hp_plugged:
            client.subscribe(cfg.topic_gpio_hp_plugged)

        self._send_connect_handshake()
        self._request_full_state()

    def _on_loop_connected(self) -> None:
        """Mark the device available. Runs before any reply queued at connect."""
        self._state = JookiState(available=True)
        self._dispatch_state()

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
        self._schedule(self._on_loop_disconnected)

    def _on_loop_disconnected(self) -> None:
        """Mark the device unavailable."""
        self._state = JookiState(available=False)
        self._dispatch_state()

    def _on_message(
        self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage
    ) -> None:
        """Copy the message onto the Home Assistant loop."""
        self._schedule(self._on_loop_message, msg.topic, bytes(msg.payload))

    def _on_loop_message(self, topic: str, payload: bytes) -> None:
        """Parse one copied message and update state. Runs in FIFO order."""
        cfg = self._device_config

        if topic == cfg.topic_state:
            self._handle_state_message(payload)
        elif topic == cfg.topic_nfc_tag:
            self._handle_nfc_tag(payload)
        elif topic == cfg.topic_nfc_tag_removed:
            self._handle_nfc_tag_removed()
        elif topic in (cfg.topic_gpio_next, cfg.topic_gpio_prev, cfg.topic_gpio_circle):
            self._handle_gpio_button(topic, payload)
        elif topic == cfg.topic_gpio_vol_set:
            self._handle_gpio_vol_set(payload)
        elif cfg.topic_gpio_hp_plugged and topic == cfg.topic_gpio_hp_plugged:
            self._handle_hp_plugged(payload)
        elif topic in (
            cfg.topic_audio_position,
            cfg.topic_audio_playing,
            cfg.topic_audio_paused,
            cfg.topic_audio_stopped,
            cfg.topic_audio_error,
            cfg.topic_audio_ended,
        ):
            self._handle_audio_event(topic, payload)
        elif topic == cfg.topic_error:
            self._handle_error(payload)

    def _handle_state_message(self, payload: bytes) -> None:
        """Handle a state update from /j/web/output/state."""
        try:
            parsed = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            _LOGGER.warning("Invalid JSON from Jooki: %s", payload[:200])
            return

        self._state.apply_slices(parsed)
        self._dispatch_state()

    def _handle_nfc_tag(self, payload: bytes) -> None:
        """Handle NFC figurine placed event."""
        try:
            parts = payload.decode().split(",")
            tag_id = parts[0] if len(parts) >= 1 else ""
            star_id = parts[1] if len(parts) >= 2 else ""
        except (UnicodeDecodeError, IndexError):
            _LOGGER.warning("Invalid NFC tag payload: %s", payload[:100])
            return

        async_dispatcher_send(
            self._hass,
            self._signal_nfc,
            "figurine_placed",
            {
                "tag_id": tag_id,
                "star_id": star_id,
                "name": figurine_label(self._state, tag_id, star_id),
            },
        )

    def _handle_nfc_tag_removed(self) -> None:
        """Handle NFC figurine removed event."""
        async_dispatcher_send(
            self._hass,
            self._signal_nfc,
            "figurine_removed",
            {},
        )

    def _handle_gpio_button(self, topic: str, payload: bytes) -> None:
        """Handle a GPIO button press/release event."""
        cfg = self._device_config
        button_map = {
            cfg.topic_gpio_next: "next",
            cfg.topic_gpio_prev: "previous",
            cfg.topic_gpio_circle: "circle",
        }
        button_name = button_map.get(topic, "unknown")

        try:
            value = payload.decode().strip()
            event_type = "pressed" if value == "1" else "released"
        except UnicodeDecodeError:
            return

        async_dispatcher_send(
            self._hass,
            self._signal_button,
            button_name,
            event_type,
        )

    def _handle_hp_plugged(self, payload: bytes) -> None:
        """Track the J2000 headphone jack (payload ``1`` or ``0``)."""
        try:
            value = payload.decode().strip()
        except UnicodeDecodeError:
            return
        if self._state.apply_hp_plugged(value):
            self._dispatch_state()

    def _handle_gpio_vol_set(self, payload: bytes) -> None:
        """Handle a physical volume knob change event."""
        try:
            parsed = json.loads(payload)
            vol = parsed.get("vol", "0")
        except (json.JSONDecodeError, UnicodeDecodeError):
            _LOGGER.warning("Invalid vol_set payload: %s", payload[:200])
            return

        async_dispatcher_send(
            self._hass,
            self._signal_volume,
            str(vol),
        )

    def _handle_audio_event(self, topic: str, payload: bytes) -> None:
        """Apply GStreamer audio events into accumulated playback state."""
        cfg = self._device_config

        if topic == cfg.topic_audio_error:
            try:
                parsed = json.loads(payload)
                _LOGGER.warning("Jooki audio error: %s", parsed)
            except (json.JSONDecodeError, UnicodeDecodeError):
                _LOGGER.warning("Jooki audio error (unparseable payload)")
            return

        event = {
            cfg.topic_audio_position: "position",
            cfg.topic_audio_playing: "playing",
            cfg.topic_audio_paused: "paused",
            cfg.topic_audio_stopped: "stopped",
            cfg.topic_audio_ended: "ended",
        }.get(topic)
        if event is None:
            return

        parsed: dict | None = None
        if event == "position":
            try:
                parsed = json.loads(payload)
            except (json.JSONDecodeError, UnicodeDecodeError):
                _LOGGER.warning(
                    "Invalid audio position payload: %s", payload[:200]
                )
                return

        update = self._state.apply_gstreamer_audio(event, parsed)
        if update == "position":
            self._dispatch_position()
        elif update == "transport":
            self._dispatch_state()

    def _handle_error(self, payload: bytes) -> None:
        """Handle an error/info message from the device."""
        try:
            parsed = json.loads(payload)
            error_msg = parsed.get("msg", "Unknown error")
            _LOGGER.info("Jooki device message: %s", error_msg)
        except (json.JSONDecodeError, UnicodeDecodeError):
            _LOGGER.warning("Invalid error payload from Jooki: %s", payload[:200])

    def _dispatch_state(self) -> None:
        """Notify entities subscribed to device state. Runs on the HA loop."""
        async_dispatcher_send(self._hass, self._signal)

    def _dispatch_position(self) -> None:
        """Notify the media player of a playback position tick."""
        async_dispatcher_send(self._hass, self._signal_position)
