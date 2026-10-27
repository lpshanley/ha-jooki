# Jooki Integration for Home Assistant

A custom [Home Assistant](https://www.home-assistant.io/) integration for the [Jooki](https://www.jooki.rocks/) children's music player, communicating directly with the device's built-in MQTT broker. Supports both J1000 (original) and J2000 (second generation) models.

## Features

- **Media Player** — Play, pause, next/previous track, volume, repeat, shuffle, shutdown, album art, and seek bar
- **Media Browser** — Browse playlists from the HA media player card
- **NFC & Button Events** — Figurine placement/removal and physical button presses as HA events for automations
- **Toy Safe Switch** — Set the maximum-volume limit
- **Battery & Power Sensors** — Battery level, temperature, voltage, charging state, and plugged-in state
- **Spotify and Deezer Status** — Account connection status
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
| Battery Temperature | Sensor | Battery temperature (°C) |
| Figurine | Sensor | Currently placed figurine name |
| Playback Source | Sensor | Current playback service |
| Current Playlist | Sensor | Title of the playlist now playing |
| Device Message | Sensor | Newest device message type, with the message list as an attribute |
| Audiobook | Binary Sensor | Whether the current item is an audiobook |
| Explicit | Binary Sensor | Whether the current track is explicit |
| WiFi Signal | Sensor | WiFi signal strength (dBm) · diagnostic |
| WiFi SSID | Sensor | Connected network name · diagnostic |
| Battery Voltage | Sensor | Battery voltage (mV) · diagnostic |
| Disk Usage | Sensor | Device storage usage (%) · diagnostic |
| Bluetooth Speaker MAC | Sensor | Connected Bluetooth speaker address · diagnostic |
| Spotify Username | Sensor | Connected Spotify account name · diagnostic |
| Deezer Username | Sensor | Connected Deezer account name · diagnostic |
| Charging | Binary Sensor | Charging state |
| Plugged In | Binary Sensor | Power cable connection state |
| Headphones | Binary Sensor | Headphone output state |
| Bluetooth Speaker | Binary Sensor | Whether a Bluetooth speaker is connected |
| Figurine Present | Binary Sensor | Whether a figurine is on the device |
| Spotify Connected | Binary Sensor | Spotify account connection · diagnostic |
| Deezer Connected | Binary Sensor | Deezer account connection · diagnostic |
| Toy Safe | Switch | Maximum-volume limit · config |
| Language | Select | Device language · config |
| LED Ring | Light | LED ring color and effects · config |
| Resync | Button | Force full state refresh · diagnostic |
| Figurine Event | Event | Figurine placed/removed events |
| Next Button | Event | Physical next button press/release |
| Previous Button | Event | Physical previous button press/release |
| Circle Button | Event | Physical circle button press/release |
| Volume Knob | Event | Physical volume knob changes |
| Skip Seconds | Service | `jooki.skip_seconds` skips forward or backward by a number of seconds |
| Dismiss Message | Service | `jooki.dismiss_message` dismisses a device message by id |

## Known Limitations

- The Jooki is battery-powered and goes offline when turned off. Entities will show as **unavailable** when the device is off and automatically reconnect when it powers back on.
- The volume range is assumed to be 0-100. This may need calibration for your device.
- The media browser requires the device to have sent its database state (happens automatically on connect via GET_STATE).

## Contributing

1. Fork the repository and create a feature branch from `main`
2. Use conventional commit messages. The type chooses the next version:
   - `feat:` — minor release
   - `fix:` — patch release
   - `feat!:` or a `BREAKING CHANGE:` footer — major release
   - `perf:` and `refactor:` are included in the notes of the next release and do not bump the version on their own
3. Open a pull request. PRs are validated with [hassfest](https://developers.home-assistant.io/docs/creating_integration_manifest/) and [HACS action](https://github.com/hacs/action)

## Releasing

Pushing to `main` runs [Release Please](https://github.com/googleapis/release-please). When `feat` or `fix` commits are waiting, it opens a release pull request that updates `CHANGELOG.md` and the version in `manifest.json`.

Merging that pull request:

- Tags the version without a `v` prefix, matching `0.1.0`
- Publishes the GitHub release and its notes
- Uploads `jooki.zip` for HACS

A release published by hand still gets `jooki.zip` from the release workflow. That workflow stamps the tag into `manifest.json` inside the archive.

## Credits

MQTT protocol details based on the reverse engineering work documented at [there.oughta.be](https://there.oughta.be/an/interface-for-jooki).
