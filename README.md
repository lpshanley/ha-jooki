# Jooki Integration for Home Assistant

A custom [Home Assistant](https://www.home-assistant.io/) integration for the [Jooki](https://www.jooki.rocks/) children's music player, communicating directly with the device's built-in MQTT broker. Supports both J1000 (original) and J2000 (second generation) models.

## Features

- **Media Player** — Play, pause, next/previous track, volume, repeat, shuffle, shutdown, album art, and seek bar
- **Media Browser** — Browse playlists and figurines directly from the HA media player card
- **Figurine Select** — Virtually place or remove a figurine from Home Assistant
- **NFC & Button Events** — Figurine placement/removal and physical button presses as HA events for automations
- **Toy Safe Switch** — Toggle the device's hearing-safe content filtering mode
- **Battery & Power Sensors** — Battery level, voltage, charging state, and plugged-in state
- **Spotify Status** — Spotify connection status
- **WiFi Diagnostics** — Signal strength, SSID, and device disk usage
- **Resync Button** — Force a full state refresh from the device on demand

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
3. Enter the device's IP address, MQTT port (default 1883), a friendly name, and select the device model (J1000 or J2000)
4. The integration will test the MQTT connection before completing setup

## Entities

Once configured, the integration creates a single device with the following entities:

| Entity | Type | Description |
|--------|------|-------------|
| Jooki | Media Player | Playback controls, volume, track info, media browser |
| Battery | Sensor | Battery level (0-100%) |
| Figurine | Sensor | Currently placed figurine name |
| WiFi Signal | Sensor | WiFi signal strength (dBm) · diagnostic |
| WiFi SSID | Sensor | Connected network name · diagnostic |
| Battery Voltage | Sensor | Battery voltage (mV) · diagnostic |
| Disk Usage | Sensor | Device storage usage (%) · diagnostic |
| Charging | Binary Sensor | Charging state |
| Plugged In | Binary Sensor | Power cable connection state |
| Headphones | Binary Sensor | Headphone output state |
| Figurine Present | Binary Sensor | Whether a figurine is on the device |
| Spotify Connected | Binary Sensor | Spotify backend connection · diagnostic |
| Toy Safe | Switch | Hearing-safe content filtering toggle · config |
| Figurine Select | Select | Virtually place/remove a figurine |
| Resync | Button | Force full state refresh · diagnostic |
| Figurine Event | Event | Figurine placed/removed events |
| Next Button | Event | Physical next button press/release |
| Previous Button | Event | Physical previous button press/release |
| Circle Button | Event | Physical circle button press/release |

## Known Limitations

- The Jooki is battery-powered and goes offline when turned off. Entities will show as **unavailable** when the device is off and automatically reconnect when it powers back on.
- The volume range is assumed to be 0-100. This may need calibration for your device.
- Media browser and figurine select require the device to have sent its database state (happens automatically on connect via GET_STATE).

## Contributing

1. Fork the repository and create a feature branch from `main`
2. Use conventional commit messages: `feat:`, `fix:`, `chore:`, `docs:`, etc.
3. Open a pull request and add a label for changelog categorization:
   - `enhancement` — new features
   - `bug` — bug fixes
   - `breaking-change` — breaking changes
   - `chore` — maintenance
4. PRs are automatically validated with [hassfest](https://developers.home-assistant.io/docs/creating_integration_manifest/) and [HACS action](https://github.com/hacs/action)

## Releasing

Releases are automated via GitHub Actions. To publish a new version:

1. Merge PRs to `main` with appropriate labels
2. Go to **Releases** → **Draft a new release**
3. Create a new tag using semantic versioning (e.g. `0.2.0`)
4. Click **Generate release notes** — PRs are auto-categorized by label
5. Click **Publish release**

The release workflow automatically:
- Stamps the tag version into `manifest.json`
- Packages the integration into a ZIP
- Uploads `jooki.zip` as a release asset

HACS picks up new releases automatically.

## Credits

MQTT protocol details based on the reverse engineering work documented at [there.oughta.be](https://there.oughta.be/an/interface-for-jooki).
