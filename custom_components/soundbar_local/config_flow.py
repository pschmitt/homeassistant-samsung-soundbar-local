"""Config flow for Samsung Soundbar Local."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import CONF_VERIFY_SSL, DOMAIN
from .helpers import get_mac_address
from .soundbar import AsyncSoundbar, SoundbarApiError


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

    async def _async_probe(self, user_input: dict[str, Any]) -> str | None:
        """Connect to the soundbar and return its MAC address, if any.

        Raises SoundbarApiError if the device can't be reached. The MAC
        lookup is best-effort (ARP-table, populated by this same request) and
        is not required for the probe to be considered successful; the
        soundbar's own `getIdentifier` is a per-*model* string, not a
        per-unit serial, so it isn't usable as a unique_id.
        """
        session = aiohttp_client.async_get_clientsession(
            self.hass, verify_ssl=user_input.get(CONF_VERIFY_SSL, False)
        )
        soundbar = AsyncSoundbar(
            host=user_input[CONF_HOST],
            session=session,
            verify_ssl=user_input.get(CONF_VERIFY_SSL, False),
        )
        await soundbar.identifier()
        return await self.hass.async_add_executor_job(
            get_mac_address, user_input[CONF_HOST]
        )

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
