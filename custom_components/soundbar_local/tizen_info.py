"""Samsung Tizen 'remote' info API (http://<host>:8001/api/v2/).

This soundbar runs the same Tizen OS/stack as Samsung Smart TVs and exposes
the same unauthenticated device-info endpoint used by the official
`samsungtv` integration. It's queried only to read the device's own display
name, model number, MAC address and firmware version - no token or pairing
is required for this GET, unlike the JSON-RPC control API on port 1516.
"""

from __future__ import annotations

import asyncio
from typing import TypedDict

import aiohttp
import async_timeout

TIZEN_INFO_PORT = 8001
TIZEN_INFO_PATH = "/api/v2/"


class TizenDeviceInfo(TypedDict, total=False):
    """Fields of interest from the Tizen device-info endpoint."""

    name: str | None
    model: str | None
    mac: str | None
    firmware: str | None
    duid: str | None


async def async_get_tizen_info(
    session: aiohttp.ClientSession, host: str, *, timeout: int = 8
) -> TizenDeviceInfo | None:
    """Return the device's self-reported name/model/MAC, or None if unreachable."""
    url = f"http://{host}:{TIZEN_INFO_PORT}{TIZEN_INFO_PATH}"
    try:
        async with async_timeout.timeout(timeout):
            resp = await session.get(url)
            resp.raise_for_status()
            data = await resp.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        return None

    if not isinstance(data, dict):
        return None

    device = data.get("device") or {}
    return TizenDeviceInfo(
        name=data.get("name") or None,
        model=device.get("ModelNumber") or None,
        mac=device.get("wifiMac") or None,
        firmware=device.get("firmwareVersion") or None,
        duid=device.get("duid") or None,
    )
