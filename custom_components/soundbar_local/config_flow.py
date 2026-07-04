"""Config flow for Samsung Soundbar Local."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import CONF_VERIFY_SSL, DOMAIN
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

    async def _async_get_identifier(self, user_input: dict[str, Any]) -> str | None:
        """Probe the soundbar and return its device identifier, if any."""
        session = aiohttp_client.async_get_clientsession(
            self.hass, verify_ssl=user_input.get(CONF_VERIFY_SSL, False)
        )
        soundbar = AsyncSoundbar(
            host=user_input[CONF_HOST],
            session=session,
            verify_ssl=user_input.get(CONF_VERIFY_SSL, False),
        )
        return await soundbar.identifier()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step when user initiates a flow via the UI."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                identifier = await self._async_get_identifier(user_input)
            except SoundbarApiError:
                errors["base"] = "cannot_connect"
            else:
                # Prefer the soundbar's own identifier as the unique_id so a
                # later IP change doesn't look like a new device; fall back
                # to the host if the device didn't return one.
                await self.async_set_unique_id(identifier or user_input[CONF_HOST])
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
                identifier = await self._async_get_identifier(user_input)
            except SoundbarApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(identifier or entry.unique_id)
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(entry, data=user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(entry.data),
            errors=errors,
        )
