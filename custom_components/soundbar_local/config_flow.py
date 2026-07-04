"""Config flow for Samsung Soundbar Local."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from .const import CONF_VERIFY_SSL, DOMAIN
from .helpers import get_mac_address
from .soundbar import AsyncSoundbar, SoundbarApiError
from .tizen_info import async_get_tizen_info


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST)): str,
            vol.Optional(
                CONF_VERIFY_SSL, default=defaults.get(CONF_VERIFY_SSL, False)
            ): bool,
        }
    )


class SoundbarLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Soundbar."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_host: str | None = None
        self._discovered_name: str | None = None

    async def _async_probe(self, user_input: dict[str, Any]) -> str | None:
        """Connect to the soundbar and return its MAC address, if any.

        Raises SoundbarApiError if the device can't be reached. `getIdentifier`
        is a per-*model* string, not a per-unit serial, so it isn't usable as
        a unique_id - the MAC (from the Tizen info endpoint, falling back to
        an ARP-table lookup) is used instead.
        """
        host = user_input[CONF_HOST]
        session = aiohttp_client.async_get_clientsession(
            self.hass, verify_ssl=user_input.get(CONF_VERIFY_SSL, False)
        )
        soundbar = AsyncSoundbar(
            host=host,
            session=session,
            verify_ssl=user_input.get(CONF_VERIFY_SSL, False),
        )
        await soundbar.identifier()

        tizen_info = await async_get_tizen_info(session, host) or {}
        mac = tizen_info.get("mac")
        if not mac:
            mac = await self.hass.async_add_executor_job(get_mac_address, host)
        return format_mac(mac) if mac else None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step when user initiates a flow via the UI."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                mac = await self._async_probe(user_input)
            except SoundbarApiError:
                errors["base"] = "cannot_connect"
            else:
                # Prefer the soundbar's MAC as the unique_id so a later IP
                # change doesn't look like a new device; fall back to the
                # host if the MAC couldn't be resolved.
                await self.async_set_unique_id(mac or user_input[CONF_HOST])
                self._abort_if_unique_id_configured(updates=user_input)
                return self.async_create_entry(
                    title=user_input[CONF_HOST], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=_schema(), errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle re-configuring an existing entry (e.g. after an IP change)."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                mac = await self._async_probe(user_input)
            except SoundbarApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(mac or entry.unique_id)
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(entry, data=user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(entry.data),
            errors=errors,
        )

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> FlowResult:
        """Handle discovery via DHCP.

        Two manifest matchers land here: the soundbar's own MAC OUI (a
        genuinely new device) and `registered_devices` (an already-configured
        soundbar that got a new DHCP lease). Both cases key off the MAC, so
        they share this one handler - the same pattern used for
        `registered_devices` matches like the roomba/samsungtv integrations.
        """
        host = discovery_info.ip
        mac = format_mac(discovery_info.macaddress)

        await self.async_set_unique_id(mac)
        # Already configured: silently repoint it at the new IP and stop -
        # this is the "device moved" case, no user interaction needed.
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        # Unknown MAC: this is a genuinely new device. The Samsung OUI is
        # shared with other product lines (TVs, phones, ...), so actively
        # probe the JSON-RPC control port before showing a discovery prompt -
        # only something that actually answers as a soundbar gets this far.
        session = aiohttp_client.async_get_clientsession(self.hass, verify_ssl=False)
        soundbar = AsyncSoundbar(host=host, session=session, verify_ssl=False)
        try:
            await soundbar.identifier()
        except SoundbarApiError:
            return self.async_abort(reason="not_soundbar_device")

        tizen_info = await async_get_tizen_info(session, host) or {}
        self._discovered_host = host
        self._discovered_name = tizen_info.get("name") or host
        self.context["title_placeholders"] = {"name": self._discovered_name}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm a DHCP-discovered soundbar before adding it."""
        if user_input is not None:
            data = {CONF_HOST: self._discovered_host, CONF_VERIFY_SSL: False}
            return self.async_create_entry(
                title=self._discovered_name or self._discovered_host, data=data
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={"name": self._discovered_name},
        )
