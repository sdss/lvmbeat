#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2024-12-21
# @Filename: tools.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from datetime import datetime, timezone


__all__ = ["timestamp_to_iso"]


def timestamp_to_iso(ts: float | None) -> str | None:
    """Converts a timestamp to an ISO string."""

    if ts is None:
        return None

    return datetime.fromtimestamp(ts, timezone.utc).isoformat().replace("+00:00", "Z")
