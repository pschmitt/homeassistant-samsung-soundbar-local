"""Network helpers for Samsung Soundbar Local.

The soundbar's local JSON-RPC API has no MAC address query, so the MAC is
looked up best-effort in the kernel neighbor (ARP) table, which gets
populated as a side effect of the HTTPS polling traffic to the device.
"""

from __future__ import annotations

import socket

ARP_PATH = "/proc/net/arp"
EMPTY_MAC = "00:00:00:00:00:00"


def get_mac_address(host: str) -> str | None:
    """Return the MAC address for a host from the neighbor table, if known.

    Blocking (DNS + file I/O) - call via an executor.
    """
    try:
        ip = socket.gethostbyname(host)
    except OSError:
        return None

    try:
        with open(ARP_PATH, encoding="ascii") as arp:
            next(arp, None)  # header
            for line in arp:
                fields = line.split()
                if len(fields) >= 4 and fields[0] == ip:
                    mac = fields[3]
                    if mac and mac != EMPTY_MAC:
                        return mac
    except OSError:
        return None
    return None
