# Samsung Soundbar **Local** – Home Assistant Integration

<img src="logo.png" alt="Samsung Soundbar Local logo" width="200">

> **Local IP control for 2024-line Samsung Wi-Fi soundbars**
> HW-Q990D · HW-Q800D · HW-QS730D · HW-S800D · HW-S801D · HW-S700D · HW-S60D · HW-S61D · HW-LS60D

This is a fork of [ZtF/hass-samsung-soundbar-local](https://github.com/ZtF/hass-samsung-soundbar-local),
kept as the source for the `soundbar_local` integration deployed from
[pschmitt/homeassistant](https://github.com/pschmitt) (see that repo's
`custom_components-local/` for the deployment convention). The domain is
`soundbar_local` (not `samsung_soundbar_local` as in the upstream folder
layout) to match what's already registered in that Home Assistant instance.

---

## What is it?

`soundbar_local` is a custom Home Assistant component that talks **directly** to your 2024 Samsung soundbar over the LAN (TCP 1516, same JSON-RPC API used by the SmartThings app).
No cloud, no SmartThings integration in Home Assistant – everything stays on your network.

### Key features

| Function | Details |
|----------|---------|
| Power control | `turn_on`, `turn_off` |
| Audio | volume **set / step / mute** |
| Subwoofer | woofer ± via `button.py` (not enabled by default, see `const.PLATFORMS`) |
| Inputs | HDMI1, E-ARC, ARC, Digital, Bluetooth, Wi-Fi |
| Sound modes | Standard, Surround, Game, Movie, Music, Clear Voice, DTS Virtual X, Adaptive |

The entity is exposed as `media_player.soundbar_<ipaddr>` and works with dashboards, automations and scripts just like any other media-player device.

### Changes from upstream

- **MAC address**: the soundbar's protocol has no MAC query, so the MAC is
  looked up best-effort in the kernel neighbor (ARP) table (populated by the
  polling traffic to the device, see `helpers.py`) and surfaced as a
  `connections` entry on the device, the same technique used in
  [homeassistant-tesmart-kvm](https://github.com/pschmitt/homeassistant-tesmart-kvm).
  Inventory tools that match HA devices by MAC (e.g. NetBox asset-tag
  matching, if the NetBox device record has the interface MAC set) can use
  this to identify the device.
- **`getIdentifier` is not a serial number**: it turns out to be a
  per-*model* string (e.g. `22_AV_HW-S67GD`, shared by every unit of that
  model), not a per-unit serial - Samsung's local API has no way to read the
  device's actual printed serial. It's surfaced as `model_id` on the device
  instead of (incorrectly) as `serial_number`.
- **Reconfigure support**: `config_flow.py` now implements
  `async_step_reconfigure`, so a device whose IP changed can be repointed via
  **Settings → Devices & Services → (device) → ⋮ → Reconfigure** instead of
  deleting and re-adding the integration. The config entry's `unique_id` is
  migrated from the IP to the device's MAC (when resolvable) so reconfiguring
  correctly recognizes "same device, new address" instead of aborting as a
  mismatch - unlike `getIdentifier`, the MAC is actually unique per physical
  unit.

---

## Supported models

* HW-Q990D  – HW-Q800D  – HW-QS730D
* HW-S800D  – HW-S801D  – HW-S700D  – HW-S60D  – HW-S61D  – HW-LS60D

> Older (2023 and below) bars do **not** implement the same API and will **not** work.

---

## Requirements

* Home Assistant 2023.12 or newer
* Python 3.11 (bundled with HA OS / Container)
* Your soundbar **added to the Samsung SmartThings app, connected to Wi-Fi** and
  **"IP control" enabled** in the device settings.
  This setting allows the bar to produce an *Access Token* that the integration uses.

---

## Installation

Copy `custom_components/soundbar_local` into your Home Assistant `custom_components/`
directory, restart Home Assistant, then go to **Settings → Devices & Services →
+ Add Integration**, search for **"Samsung Soundbar Local"**, enter the
soundbar's IP address and confirm.

---

## Branding

This repository bundles a modified version of the official SmartThings icon
(`brand/`, `icon.png`, `logo.png`) with an "L" badge added to distinguish this
**local**-polling integration from the official cloud-based SmartThings
integration in the Home Assistant UI. SmartThings and related marks belong to
Samsung Electronics. The integration code is MIT-licensed (see `LICENSE`), but
the bundled Samsung/SmartThings artwork is not relicensed under MIT.

## License

MIT, see `LICENSE`. Original work Copyright (c) 2025 ZtF.
