"""Media Player entity for Samsung Soundbar Local."""

from __future__ import annotations

import logging

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, format_mac
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .soundbar import AsyncSoundbar

_LOGGER = logging.getLogger(__name__)

_SUPPORTED: MediaPlayerEntityFeature = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.SELECT_SOUND_MODE
)

_SOURCES = [
    "HDMI_IN1",
    "HDMI_IN2",
    "E_ARC",
    "ARC",
    "D_IN",
    "BT",
    "WIFI_IDLE",
]

_SOUND_MODES = [
    "STANDARD",
    "SURROUND",
    "GAME",
    "MOVIE",
    "MUSIC",
    "CLEARVOICE",
    "DTS_VIRTUAL_X",
    "ADAPTIVE",
]


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities):
    """Set up the soundbar platform from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    soundbar: AsyncSoundbar = data["soundbar"]

    async_add_entities([SoundbarLocalEntity(coordinator, soundbar, entry, data)], True)


class SoundbarLocalEntity(CoordinatorEntity, MediaPlayerEntity):
    """Representation of the soundbar as a Media Player entity."""

    _attr_supported_features = _SUPPORTED
    _attr_source_list = _SOURCES
    _attr_sound_mode_list = _SOUND_MODES
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER

    def __init__(
        self,
        coordinator,
        soundbar: AsyncSoundbar,
        entry: ConfigEntry,
        data: dict,
    ) -> None:
        super().__init__(coordinator)
        self._soundbar = soundbar
        self._entry = entry

        host = entry.data["host"]
        mac = data.get("mac")
        # The device's own name (e.g. "Living room speaker", as set in the
        # SmartThings app), read from the Tizen info endpoint - falls back to
        # a generic name if that endpoint wasn't reachable.
        name = data.get("device_name") or f"Soundbar {host}"

        self._attr_unique_id = host
        self._attr_name = name
        connections = {(CONNECTION_NETWORK_MAC, format_mac(mac))} if mac else set()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host)},
            connections=connections,
            manufacturer="Samsung",
            # Links the device page's "Visit" button at the soundbar's own
            # local JSON-RPC control API. It won't render anything useful in
            # a browser (it only speaks JSON-RPC POST), but it's a handy
            # one-click way to confirm the host/port this integration talks to.
            configuration_url=f"https://{host}:1516/",
            model=data.get("model") or "Soundbar",
            # getIdentifier() returns a per-*model* string (e.g.
            # "22_AV_HW-S67GD"), not a per-unit serial - expose it as the
            # model identifier, not as serial_number.
            model_id=coordinator.data.get("identifier"),
            # The real, printed serial - from the UPnP "IP Control"
            # descriptor (port 9110), not from the JSON-RPC/Tizen APIs.
            # Passed explicitly (even when None) rather than omitted, since
            # an earlier revision incorrectly set this to the model_id value
            # and omitting the key would leave that stale value in place.
            serial_number=data.get("serial_number"),
            sw_version=data.get("firmware"),
            name=name,
        )

    # ---------- control ----------
    async def async_turn_on(self) -> None:
        await self._soundbar.power_on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        await self._soundbar.power_off()
        await self.coordinator.async_request_refresh()

    async def async_volume_up(self) -> None:
        await self._soundbar.volume_up()
        await self.coordinator.async_request_refresh()

    async def async_volume_down(self) -> None:
        await self._soundbar.volume_down()
        await self.coordinator.async_request_refresh()

    async def async_set_volume_level(self, volume: float) -> None:
        # round(), not int(): truncating float->int here systematically
        # rounds down (e.g. a 0.5 slider position can compute as 49.999...
        # and land on 49 instead of 50).
        await self._soundbar.set_volume(round(volume * 100))
        await self.coordinator.async_request_refresh()

    async def async_mute_volume(self, mute: bool) -> None:
        if mute != self.is_volume_muted:
            await self._soundbar.mute_toggle()
            await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str) -> None:
        await self._soundbar.select_input(source)
        await self.coordinator.async_request_refresh()

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        await self._soundbar.set_sound_mode(sound_mode)
        await self.coordinator.async_request_refresh()

    # ---------- properties ----------
    @property
    def state(self):
        power = self.coordinator.data.get("power")
        return STATE_ON if power == "powerOn" else STATE_OFF

    @property
    def volume_level(self):
        return self.coordinator.data.get("volume", 0) / 100

    @property
    def is_volume_muted(self):
        return self.coordinator.data.get("mute", False)

    @property
    def source(self):
        return self.coordinator.data.get("input")

    @property
    def sound_mode(self):
        return self.coordinator.data.get("sound_mode")

    # ---------- coordinator update ----------
    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
