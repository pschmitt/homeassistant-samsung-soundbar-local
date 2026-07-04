"""Samsung "IP Control" UPnP device description.

http://<host>:9110/ip_control is the UPnP root-device descriptor for
urn:samsung.com:device:IPControlServer:1, the same one SSDP advertises
(M-SEARCH to udp/1900 on the device returns a LOCATION header pointing
here). It's fetched directly by URL/port instead of via SSDP multicast,
since UDP multicast rarely reaches Home Assistant's network namespace
reliably (Docker, VLANs, ...).

This is the only endpoint found so far that has the device's actual printed
serial number - neither the JSON-RPC control API (port 1516) nor the Tizen
info endpoint (port 8001) expose it.
"""

from __future__ import annotations

import asyncio
from typing import TypedDict
from xml.etree import ElementTree

import aiohttp
import async_timeout

UPNP_INFO_PORT = 9110
UPNP_INFO_PATH = "/ip_control"
_NS = "{urn:samsung.com:device-1-0}"


class UpnpDeviceInfo(TypedDict, total=False):
    """Fields of interest from the UPnP device descriptor."""

    serial_number: str | None
    friendly_name: str | None
    model_name: str | None


async def async_get_upnp_info(
    session: aiohttp.ClientSession, host: str, *, timeout: int = 8
) -> UpnpDeviceInfo | None:
    """Return the device's UPnP-advertised serial/name/model, or None."""
    url = f"http://{host}:{UPNP_INFO_PORT}{UPNP_INFO_PATH}"
    try:
        async with async_timeout.timeout(timeout):
            resp = await session.get(url)
            resp.raise_for_status()
            text = await resp.text()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return None

    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return None

    device = root.find(f"{_NS}device")
    if device is None:
        return None

    def _text(tag: str) -> str | None:
        element = device.find(f"{_NS}{tag}")
        return element.text.strip() if element is not None and element.text else None

    return UpnpDeviceInfo(
        serial_number=_text("serialNumber"),
        friendly_name=_text("friendlyName"),
        model_name=_text("modelName"),
    )
