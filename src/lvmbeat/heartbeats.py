#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2024-12-20
# @Filename: heartbeats.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import time

from typing import NotRequired, TypedDict


class HeartbeatData(TypedDict):
    """Data to create a heartbeat."""

    name: str
    critical: NotRequired[bool]


class Heartbeats(dict[str, "Heartbeat"]):
    """Collection of heartbeats."""

    def __init__(self, data: list[HeartbeatData] = []):
        dict.__init__({})
        for heartbeat_data in data:
            self[heartbeat_data["name"]] = Heartbeat(
                heartbeat_data["name"],
                critical=heartbeat_data.get("critical", True),
            )

    def seen_since(self, delta: float = 30):
        """Returns which components have been seen in the last ``delta`` seconds."""

        response: dict[str, bool] = {}

        for key, heartbeat in self.items():
            heartbeat_delta = heartbeat.time_delta()
            response[key] = heartbeat_delta is not None and heartbeat_delta < delta

        return response


class Heartbeat:
    """Tracks and updates the heartbeat of a component."""

    def __init__(self, name: str, critical: bool = True):
        self.name = name
        self.critical = critical
        self.last_set: float | None = None

    def set(self):
        """Sets the heartbeat to the current time."""

        self.last_set = time.time()

    def time_delta(self):
        """Returns the number of seconds since the last heartbeat."""

        if self.last_set is None:
            return None

        return time.time() - self.last_set
