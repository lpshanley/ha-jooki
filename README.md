# Jooki Integration for Home Assistant

A custom [Home Assistant](https://www.home-assistant.io/) integration for the [Jooki](https://www.jooki.rocks/) children's music player, communicating directly with the device's built-in MQTT broker.

## Features

- **Media Player** — Play, pause, next/previous track, volume control, and shutdown
- **Battery Sensor** — Current battery level as a percentage
- **Charging Sensor** — Whether the device is currently charging
- **LED Ring Light** — RGB color control for the Jooki's LED ring

## Prerequisites

- Jooki device on the same local network as your Home Assistant instance
- Static IP address assigned to the Jooki (recommended)

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to **Integrations**
3. Click the three-dot menu and select **Custom repositories**
4. Add `https://github.com/lpshanley/ha-jooki` with category **Integration**
5. Search for "Jooki" and install it
6. Restart Home Assistant

### Manual

1. Copy the `custom_components/jooki` directory into your Home Assistant `custom_components` folder
2. Restart Home Assistant

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for **Jooki**
3. Enter the device's IP address, MQTT port (default 1883), and a friendly name
4. The integration will test the MQTT connection before completing setup

## Entities

Once configured, the integration creates a single device with four entities:

| Entity | Type | Description |
|--------|------|-------------|
| Jooki | Media Player | Playback controls, volume, current track info |
| Battery | Sensor | Battery level (0-100%) |
| Charging | Binary Sensor | Charging state (on/off) |
| LED Ring | Light | RGB color control for the LED ring |

## Known Limitations

- The Jooki is battery-powered and goes offline when turned off. Entities will show as **unavailable** when the device is off and automatically reconnect when it powers back on.
- LED state is **optimistic** — the Jooki does not report its LED state, so the integration tracks it locally.
- The volume range is assumed to be 0-100. This may need calibration for your device.

## Credits

MQTT protocol details based on the reverse engineering work documented at [there.oughta.be](https://there.oughta.be/an/interface-for-jooki).
