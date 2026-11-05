# Device control

This fork of [Samsung Soundbar Local](https://github.com/ZtF/hass-samsung-soundbar-local)
uses the `soundbar_local` Home Assistant domain. It controls supported 2024
Samsung Wi-Fi soundbars over the LAN using JSON-RPC on TCP port 1516, without
a SmartThings cloud integration in Home Assistant. The soundbar must first be
added to the SmartThings app, connected to Wi-Fi, and have **IP control**
enabled in its settings to provide the access token used by the integration.
Home Assistant 2023.12 or later is required. Earlier soundbar generations do
not implement this protocol.

Supported 2024 models include HW-Q990D, HW-Q800D, HW-QS730D, HW-S800D,
HW-S801D, HW-S700D, HW-S60D, HW-S61D and HW-LS60D. The media player offers
power, volume, mute, HDMI1/E-ARC/ARC/Digital/Bluetooth/Wi-Fi inputs and
Standard, Surround, Game, Movie, Music, Clear Voice, DTS Virtual X and
Adaptive sound modes. Optional subwoofer buttons are not enabled by default.

## Identification and discovery

The control protocol's `getIdentifier` value identifies a model, not a unit;
it appears as `model_id`. The actual serial number comes from the UPnP
`ip_control` descriptor on port 9110. The MAC is resolved from the local
neighbor table when available. DHCP discovery reads the device's own name,
model and MAC from its Tizen information endpoint on port 8001. A matching
registered device can be repointed automatically when its IP changes;
**Reconfigure** can also change the address manually.

## Volume

The soundbar has relative volume steps, not an absolute set-volume command.
The integration reads the actual device volume after each step so lost or
coalesced commands do not cause a simulated counter to drift. While a larger
adjustment is in progress, Home Assistant shows the requested volume
optimistically; polling replaces it with the measured value afterwards.
