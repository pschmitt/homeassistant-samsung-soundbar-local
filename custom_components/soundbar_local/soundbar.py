"""
Asynchronous client for Samsung soundbar.

Should work on HW-Q990D, HW-Q930D, HW-Q800D, HW-QS730D, HW-S800D, HW-S801D, HW-S700D, HW-S60D, HW-S61D, HW-LS60D

The soundbar issues a single access token; each createAccessToken call invalidates the
previous one, so any other client (the SmartThings app, another tool) can invalidate the
token this client is holding. Responses carrying neither "result" nor "error" (for example
{"code": -32700, "message": "Parse error"}) are therefore expected. They are surfaced as
SoundbarApiError, and a failed call re-authenticates once and retries, except for an
unsupported method (-32601).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp
import async_timeout

_LOGGER = logging.getLogger(__name__)

# JSON-RPC "method not found": the model lacks this call
_METHOD_NOT_FOUND = -32601


class SoundbarApiError(Exception):
    """Raised when the soundbar API returns an error."""

    def __init__(self, message: Any, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class AsyncSoundbar:
    """Async client class."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
        *,
        port: int = 1516,
        verify_ssl: bool = False,
        timeout: int = 8,
    ) -> None:
        self._url = f"https://{host}:{port}/"
        self._session = session
        self._verify_ssl = verify_ssl
        self._timeout = timeout
        self._token: str | None = None
        self._volume_control_supported = True
        self._mute_control_supported = True
        # The soundbar's JSON-RPC server fails on concurrent requests (a poll
        # overlapping a command), so serialize them.
        self._lock = asyncio.Lock()

    # ------------------ internal helpers ------------------
    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw = json.dumps(payload, separators=(",", ":"))
        try:
            async with self._lock, async_timeout.timeout(self._timeout):
                resp = await self._session.post(
                    self._url,
                    data=raw,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    ssl=self._verify_ssl,
                )
                resp.raise_for_status()
                # Parsed here, not with resp.json(): the device answers some
                # rejections with a non-JSON content type.
                text = await resp.text()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise SoundbarApiError(str(err)) from err

        try:
            data = json.loads(text)
        except ValueError as err:
            raise SoundbarApiError(f"invalid JSON response: {text[:200]!r}") from err

        if "error" in data:
            error = data["error"]
            raise SoundbarApiError(
                error, code=error.get("code") if isinstance(error, dict) else None
            )
        if "result" not in data:
            # e.g. {"code": -32700, "message": "Parse error"} for a stale token
            raise SoundbarApiError(f"unexpected response: {data}", code=data.get("code"))
        return data["result"]

    async def _call(self, method: str, **params: Any):
        if method == "createAccessToken":
            return await self._post({"jsonrpc": "2.0", "method": method, "id": 1})

        attempts = 0
        while True:
            if not self._token:
                await self.create_token()
            params["AccessToken"] = self._token
            payload = {"jsonrpc": "2.0", "method": method, "id": 1, "params": params}
            try:
                return await self._post(payload)
            except SoundbarApiError as err:
                if err.code == _METHOD_NOT_FOUND or attempts >= 1:
                    raise
                attempts += 1
                # Drop the cached token and re-authenticate once.
                _LOGGER.debug("soundbar call %s failed; re-authenticating and retrying", method)
                self._token = None
                await asyncio.sleep(0.5)

    # ------------------ public API ------------------
    async def create_token(self) -> str:
        self._token = (await self._call("createAccessToken"))["AccessToken"]
        return self._token

    # Power ----------------------------------
    async def power_on(self):
        await self._call("powerControl", power="powerOn")

    async def power_off(self):
        await self._call("powerControl", power="powerOff")

    # Volume & mute --------------------------
    async def volume_up(self):
        await self._call("remoteKeyControl", remoteKey="VOL_UP")

    async def volume_down(self):
        await self._call("remoteKeyControl", remoteKey="VOL_DOWN")

    async def sub_plus(self):
        await self._call("remoteKeyControl", remoteKey="WOOFER_PLUS")

    async def sub_minus(self):
        await self._call("remoteKeyControl", remoteKey="WOOFER_MINUS")

    async def mute_toggle(self):
        await self._call("remoteKeyControl", remoteKey="MUTE")

    async def set_volume(self, level: int):
        """Set the volume to `level`.

        Uses the one-request volumeControl call. Models without it answer
        "method not found" and fall back to stepping, see _step_volume().
        """
        if not 0 <= level <= 100:
            raise ValueError("Volume has to be in range 0–100")
        if self._volume_control_supported:
            try:
                result = await self._call("volumeControl", volume=level)
            except SoundbarApiError as err:
                if err.code != _METHOD_NOT_FOUND:
                    raise
                self._volume_control_supported = False
            else:
                if not result.get("success", True):
                    raise SoundbarApiError(f"Failed to set volume to {level}")
                return
        await self._step_volume(level)

    async def _step_volume(self, level: int):
        """Step the volume up/down until it reaches `level`.

        There's no direct "set to N" call, only relative VOL_UP/VOL_DOWN
        steps, so this re-reads the actual device volume after every step
        instead of trusting a locally-simulated counter. A single VOL_UP/
        VOL_DOWN doesn't always move the volume by exactly 1 (it can be
        coalesced or dropped under rapid calls), so assuming it does drifts
        the simulated value away from the real one - which is what then
        shows up as a "weird in-between" volume once the coordinator polls
        the device's actual state.
        """
        current = await self.volume()
        stalled = 0
        while current != level:
            if current < level:
                await self.volume_up()
            else:
                await self.volume_down()
            new = await self.volume()
            stalled = stalled + 1 if new == current else 0
            current = new
            if stalled >= 3:
                # The device isn't moving anymore (e.g. hit a hard limit) -
                # stop instead of spinning forever.
                break

    async def set_mute(self, mute: bool) -> None:
        """Set mute, using the MUTE toggle key when muteControl is unavailable."""
        if self._mute_control_supported:
            try:
                result = await self._call("muteControl", mute=mute)
            except SoundbarApiError as err:
                if err.code != _METHOD_NOT_FOUND:
                    raise
                self._mute_control_supported = False
            else:
                if not result.get("success", True):
                    raise SoundbarApiError(f"Failed to set mute to {mute}")
                return
        if await self.is_muted() != mute:
            await self.mute_toggle()

    # Input & sound mode ---------------------
    async def select_input(self, src: str):
        await self._call("inputSelectControl", inputSource=src)

    async def set_sound_mode(self, mode: str):
        await self._call("soundModeControl", soundMode=mode)

    # Helpers --------------------------------
    async def volume(self) -> int:
        return int((await self._call("getVolume"))["volume"])

    async def is_muted(self) -> bool:
        return bool((await self._call("getMute"))["mute"])

    async def input(self) -> str:
        return (await self._call("inputSelectControl"))["inputSource"]

    async def sound_mode(self) -> str:
        return (await self._call("soundModeControl"))["soundMode"]

    async def power_state(self) -> str:
        return (await self._call("powerControl"))["power"]

    async def codec(self) -> str | None:
        return (await self._call("getCodec")).get("codec")

    async def identifier(self) -> str | None:
        return (await self._call("getIdentifier")).get("identifier")

    async def status(self) -> dict[str, Any]:
        """Return a consolidated status dict.

        Only power is required. Optional fields a model lacks come back as
        None instead of failing the whole poll.
        """
        status: dict[str, Any] = {"power": await self.power_state()}
        for key, getter in (
            ("volume", self.volume),
            ("mute", self.is_muted),
            ("input", self.input),
            ("sound_mode", self.sound_mode),
            ("codec", self.codec),
            ("identifier", self.identifier),
        ):
            try:
                status[key] = await getter()
            except (SoundbarApiError, KeyError, TypeError, ValueError):
                status[key] = None
        return status
