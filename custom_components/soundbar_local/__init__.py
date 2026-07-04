"""Main integration file for Samsung Soundbar Local."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_VERIFY_SSL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .helpers import get_mac_address
from .soundbar import AsyncSoundbar, SoundbarApiError
from .tizen_info import async_get_tizen_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Samsung Soundbar from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    session: ClientSession = aiohttp_client.async_create_clientsession(
        hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, False)
    )
    soundbar = AsyncSoundbar(
        host=entry.data[CONF_HOST],
        session=session,
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, False),
    )

    async def _async_update_data() -> dict[str, Any]:
        try:
            return await soundbar.status()
        except SoundbarApiError as err:
            raise UpdateFailed(err) from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"soundbar_{entry.data[CONF_HOST]}",
        update_method=_async_update_data,
        update_interval=timedelta(seconds=DEFAULT_POLL_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    # `getIdentifier` turns out to be a per-*model* string (e.g.
    # "22_AV_HW-S67GD"), not a per-unit serial - it's shared by every soundbar
    # of the same model, so it's exposed as model_id (see media_player.py)
    # but must not be used to key unique_id or serial_number.
    identifier = coordinator.data.get("identifier")

    # This soundbar runs the same Tizen stack as Samsung Smart TVs and
    # exposes the same unauthenticated info endpoint (port 8001), which
    # conveniently has the device's own display name, model number, MAC and
    # firmware version - none of which are available over the JSON-RPC
    # control API on port 1516.
    tizen_info = await async_get_tizen_info(session, entry.data[CONF_HOST]) or {}
    device_name = tizen_info.get("name")
    model = tizen_info.get("model")
    firmware = tizen_info.get("firmware")

    mac = tizen_info.get("mac")
    if not mac:
        # Fall back to a best-effort ARP-table lookup (same technique as
        # homeassistant-tesmart-kvm) if the Tizen endpoint didn't answer.
        mac = await hass.async_add_executor_job(get_mac_address, entry.data[CONF_HOST])
    if mac:
        mac = format_mac(mac)

    # The soundbar's IP is used as the config entry's unique_id historically,
    # but it's a connection detail, not a stable device identity - it changes
    # if the device gets a new DHCP lease. Once we have the device's MAC
    # (genuinely unique per physical unit), migrate the unique_id to it so a
    # later reconfigure (IP change) can tell "same device, new address" apart
    # from "different device" via _abort_if_unique_id_mismatch().
    if mac and entry.unique_id != mac:
        hass.config_entries.async_update_entry(entry, unique_id=mac)

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "soundbar": soundbar,
        "identifier": identifier,
        "mac": mac,
        "device_name": device_name,
        "model": model,
        "firmware": firmware,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
