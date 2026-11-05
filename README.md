<p align="center">
  <img src="logo.png" width="128" alt="Samsung Soundbar Local logo">
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/marketplace_repository/?owner=pschmitt&amp;repository=homeassistant-samsung-soundbar-local&amp;category=integration"><img src="https://my.home-assistant.io/badges/marketplace_repository.svg" alt="Open this integration in Home Assistant Marketplace"></a>
</p>

<h1 align="center">Samsung Soundbar Local</h1>

<p align="center">Control supported 2024 Samsung Wi-Fi soundbars over the local network.</p>

This is a fork of [ZtF's Samsung Soundbar Local](https://github.com/ZtF/hass-samsung-soundbar-local).
It uses the `soundbar_local` integration domain and requires Home Assistant
2023.12 or later. See [Device control](docs/device-control.md) for models and
requirements.

## Features

- **Media playback:** Turn the soundbar on or off and adjust volume, mute, input and sound mode.
- **Local API:** Use the soundbar's LAN JSON-RPC interface rather than a Home Assistant cloud integration.
- **Device discovery:** Identify the unit by its serial and MAC where available, and follow DHCP address changes. See [Device control](docs/device-control.md).
- **Reconfiguration:** Change the soundbar's address from the integration UI.

## Install

Use the Marketplace badge above on Home Assistant 2026.11 or later to add this
repository as a custom integration. On older versions, add it as a HACS
custom repository of type **Integration**. Install and restart Home Assistant.
The badge does not imply a public catalog listing. For manual installation,
copy `custom_components/soundbar_local/` into Home Assistant's
`custom_components/` directory and restart.

## Quick start

1. Add the soundbar to SmartThings and enable **IP control** on the device.
2. Add **Samsung Soundbar Local** under **Settings → Devices & services → Add integration**.
3. Enter the soundbar's address, then use the media player entity to select an input or change volume.

## Documentation

| Topic | Description |
|-------|-------------|
| [Device control](docs/device-control.md) | Supported models, identification, DHCP discovery and volume |

## License

[MIT](LICENSE). Samsung/SmartThings artwork belongs to Samsung and is not
relicensed under MIT.
