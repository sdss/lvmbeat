#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2024-12-21
# @Filename: tools.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from datetime import datetime, timezone

from nmap3 import NmapHostDiscovery

from sdsstools.utils import run_in_executor


__all__ = ["timestamp_to_iso", "is_host_up"]


def timestamp_to_iso(ts: float | None, timespec: str = "seconds") -> str | None:
    """Converts a timestamp to an ISO string."""

    if ts is None:
        return None

    return (
        datetime.fromtimestamp(ts, timezone.utc)
        .isoformat(timespec=timespec)
        .replace("+00:00", "Z")
    )


async def is_host_up(host: str) -> bool:
    """Returns whether a host is up.

    Parameters
    ----------
    host
        The host to check.

    Returns
    -------
    is_up
        ``True`` if the host is up, ``False`` otherwise.

    """

    nmap = NmapHostDiscovery()
    result = await run_in_executor(
        nmap.nmap_no_portscan,
        host,
        args="--host-timeout=1 --max-retries=2",
    )

    if (
        host not in result
        or "state" not in result[host]
        or "state" not in result[host]["state"]
    ):
        return False

    return result[host]["state"]["state"] == "up"
