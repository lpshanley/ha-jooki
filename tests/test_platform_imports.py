"""Platform modules must not reach MQTT topics or the client."""

from __future__ import annotations

import ast
from pathlib import Path

_PACKAGE = Path(__file__).resolve().parents[1] / "custom_components" / "jooki"

_PLATFORM_MODULES = (
    "binary_sensor.py",
    "button.py",
    "event.py",
    "light.py",
    "media_player.py",
    "select.py",
    "sensor.py",
    "switch.py",
)

_FORBIDDEN_IMPORT_NAMES = frozenset(
    {"paho", "mqtt_client", "JookiDeviceConfig", "get_device_config"}
)


def _dotted_import_reason(dotted: str) -> str | None:
    """Return ``paho`` or ``mqtt_client`` when ``dotted`` imports either."""
    parts = dotted.split(".")
    if "paho" in parts:
        return "paho"
    if "mqtt_client" in parts:
        return "mqtt_client"
    return None


def _violations(tree: ast.AST) -> list[str]:
    """Import and ``topic_`` attribute violations in ``tree``."""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                reason = _dotted_import_reason(alias.name)
                if reason is None and alias.name in _FORBIDDEN_IMPORT_NAMES:
                    reason = alias.name
                if reason is not None:
                    found.append(f"line {node.lineno}: imports {reason}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            reason = _dotted_import_reason(module)
            if reason is not None:
                found.append(f"line {node.lineno}: imports {reason}")
            for alias in node.names:
                if alias.name in _FORBIDDEN_IMPORT_NAMES:
                    found.append(f"line {node.lineno}: imports {alias.name}")
                elif alias.name == "*" and (
                    reason is not None or module == "device_config" or module.endswith(".device_config")
                ):
                    found.append(f"line {node.lineno}: imports JookiDeviceConfig")
        elif isinstance(node, ast.Attribute) and (
            node.attr.startswith("topic_")
            or node.attr in {"async_publish", "device_config"}
        ):
            found.append(f"line {node.lineno}: attribute {node.attr}")
        elif isinstance(node, ast.Name) and node.id.startswith("topic_"):
            found.append(f"line {node.lineno}: name {node.id}")
        elif isinstance(node, ast.keyword) and node.arg and node.arg.startswith("topic_"):
            found.append(f"line {node.lineno}: keyword {node.arg}")
    return found


def test_platform_modules_do_not_reach_mqtt_or_topics():
    """The eight platform modules stay off paho, the client, and topic fields."""
    failures: list[str] = []
    for filename in _PLATFORM_MODULES:
        path = _PACKAGE / filename
        if not path.is_file():
            failures.append(f"{filename}: missing")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations = _violations(tree)
        if violations:
            failures.append(f"{filename}: " + "; ".join(violations))
    assert not failures, "\n".join(failures)


def test_import_check_parses_syntax_and_ignores_command_names():
    """``async_send_nfc_tag`` is allowed; topic, publish, and config access are not."""
    allowed = (
        "async def send(self):\n"
        "    await self._client.async_send_nfc_tag(payload)\n",
        '"""Mentions topic_state only in prose."""\n'
        "note = 'topic_do_play'\n",
        "from .const import DOMAIN, SIGNAL_STATE_UPDATED\n"
        "from .device_commands import JookiDevice\n",
    )
    rejected = (
        "import paho.mqtt.client as mqtt\n",
        "from .mqtt_client import JookiMqttClient\n",
        "from .device_config import JookiDeviceConfig\n",
        "from .const import get_device_config\n",
        "value = client.topic_do_play\n",
        "value = client.topic_state\n",
        "await client.async_publish(topic, payload)\n",
        "cfg = client.device_config\n",
    )
    for source in allowed:
        assert not _violations(ast.parse(source)), source
    for source in rejected:
        assert _violations(ast.parse(source)), source
