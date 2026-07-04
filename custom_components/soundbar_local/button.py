"""Button entities for Samsung Soundbar Local."""

from __future__ import annotations

from collections.abc import Callable, Awaitable

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, format_mac
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .soundbar import AsyncSoundbar


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    """Set up button entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    soundbar: AsyncSoundbar = data["soundbar"]
    host = entry.data["host"]

    async_add_entities(
        [
            SoundbarWooferButton(
                coordinator,
                soundbar,
                host,
                data,
                "woofer_plus",
                "Woofer +",
                soundbar.sub_plus,
            ),
            SoundbarWooferButton(
                coordinator,
                soundbar,
                host,
                data,
                "woofer_minus",
                "Woofer -",
                soundbar.sub_minus,
            ),
        ],
        True,
    )


class SoundbarWooferButton(CoordinatorEntity, ButtonEntity):
    """Representation of a woofer control button."""

    def __init__(
        self,
        coordinator,
        soundbar: AsyncSoundbar,
        host: str,
        data: dict,
        unique_suffix: str,
        label: str,
        action: Callable[[], Awaitable[None]],
    ) -> None:
        super().__init__(coordinator)
        self._soundbar = soundbar
        self._attr_unique_id = f"{host}_{unique_suffix}"

        mac = data.get("mac")
        device_name = data.get("device_name") or f"Soundbar {host}"
        self._attr_name = f"{device_name} {label}"
        connections = {(CONNECTION_NETWORK_MAC, format_mac(mac))} if mac else set()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host)},
            connections=connections,
            manufacturer="Samsung",
            model=data.get("model") or "Soundbar",
            model_id=coordinator.data.get("identifier"),
            sw_version=data.get("firmware"),
            name=device_name,
        )
        self._action = action

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._action()
        await self.coordinator.async_request_refresh()
