#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2024-12-20
# @Filename: actor.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio
import os
from time import time

from typing import Annotated, TypedDict

import click
import httpx
from pydantic import BaseModel, Field

from clu.actor import AMQPActor
from clu.command import Command
from clu.parsers.click import command_parser
from sdsstools import cancel_task

from lvmbeat import config
from lvmbeat.heartbeats import HeartbeatData, Heartbeats
from lvmbeat.tools import is_host_up, timestamp_to_iso


class HeartbeatSchema(BaseModel):
    """Schema for a heartbeat."""

    current: Annotated[
        bool,
        Field(description="Whether the heartbeat has been seen and is active."),
    ]
    last_seen: Annotated[
        str | None,
        Field(description="ISO date of the last time the heartbeat was seen."),
    ]


class BeatKeywordSchema(BaseModel):
    """Reply schema for :obj:`.BeatActor`."""

    heartbeats: Annotated[
        dict[str, HeartbeatSchema],
        Field(description="Status of the component heartbeats."),
    ]
    last_emitted_ecp: Annotated[
        str | None,
        Field(description="ISO date of the last hearbeat sent to the ECP."),
    ]
    last_emitted_outside: Annotated[
        str | None,
        Field(
            description="ISO date of the last successful "
            "heartbeat sent to the outside world monitoring tool."
        ),
    ]
    network: Annotated[
        NetworkStatus,
        Field(description="Network status."),
    ]


class NetworkStatus(TypedDict):
    """Network status."""

    lco: bool
    outside: bool


class BeatActor(AMQPActor):
    """Heartbeat actor."""

    parser = command_parser

    def __init__(self, *args, heartbeats: list[HeartbeatData] = [], **kwargs):
        if "schema" not in kwargs:
            kwargs["schema"] = BeatKeywordSchema

        super().__init__(*args, **kwargs)

        # Number of seconds after which a heartbeat is considered to be down.
        self.timeout: float = self.config.get("timeout", 30)

        # Create the heartbeats instance. The information is usually passed
        # in the configuration as the heartbeats key.
        heartbeat_data = heartbeats or self.config.get("heartbeats", [])
        self.heartbeats = Heartbeats(heartbeat_data)

        # Last heartbeat emitted to the ECP
        self._last_emitted_ecp: float | None = None

        # Last time we emitted the outside world heartbeat.
        self._last_emitted_outside: float | None = None

        # Track network access to other LCO services and the outside world.
        self.network_status: NetworkStatus = {
            "lco": True,
            "outside": True,
        }

        self._emit_outside_task = asyncio.create_task(self.emit_outside())
        self._network_status_task = asyncio.create_task(self.update_network_status())

    async def stop(self):
        """Stops the actor."""

        self._emit_outside_task = await cancel_task(self._emit_outside_task)

        return await super().stop()

    async def update(self):
        """Callback called when a heartbeat gets updated.

        If all the critical heartbeats are present, emits the dome heartbeat.

        """

        seen_hbs = self.heartbeats.seen_since(self.timeout)
        for hb_name, seen in seen_hbs.items():
            hb = self.heartbeats[hb_name]
            if seen is False:
                if hb.critical is True:
                    self.log.warning(
                        f"Heartbeat for {hb_name!r} has not been seen "
                        f"in the last {self.timeout} seconds."
                    )
                    return
                else:
                    self.log.warning(
                        f"Heartbeat for {hb_name!r} has not been seen "
                        f"in the last {self.timeout} seconds. "
                        "Skipping since it is not critical."
                    )

        if self._last_emitted_ecp and time() - self._last_emitted_ecp < 10:
            # Prevent emitting the heartbeat too often.
            return

        self.log.info("Emitting dome heartbeat.")
        cmd = await self.send_command("lvmecp", "heartbeat")
        if not cmd.status.did_succeed:
            self.log.error(
                "Possible error emitting dome heartbeat. "
                "The lcmecp heartbeat command failed."
            )
        else:
            self._last_emitted_ecp = time()

    async def emit_outside(self):
        """Emits a heartbeat to the outside world."""

        outside_url = os.getenv(
            "LVMBEAT_OUTSIDE_MONITOR_URL",
            config["outside_monitor"]["url"],
        )

        if not outside_url:
            self.log.warning(
                "No outside monitor URL defined. Will not emit "
                "heartbeats to the outside world."
            )
            return

        if "/heartbeat" not in outside_url:
            outside_url = outside_url.rstrip("/") + "/heartbeat"

        interval = self.config.get("outside_monitor", {}).get("interval", 15)

        while True:
            async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
                try:
                    response = await client.get(outside_url)
                    response.raise_for_status()
                except Exception as ee:
                    self.log.error(f"Error emitting heartbeat to {outside_url!r}: {ee}")
                else:
                    self.log.debug(f"Emitted heartbeat to {outside_url!r}.")
                    self._last_emitted_outside = time()

            await asyncio.sleep(interval)

    async def update_network_status(self):
        """Updates the network status."""

        while True:
            self.log.debug("Updating network status.")

            internet = await is_host_up("8.8.8.8")  # Google DNS
            lco = await is_host_up("10.8.8.46")  # clima.lco.cl

            self.network_status["outside"] = internet
            self.network_status["lco"] = lco

            await asyncio.sleep(15)


BeatCommand = Command[BeatActor]


@command_parser.command()
async def status(command: BeatCommand):
    """Outputs the status of the heartbeats."""

    seen = command.actor.heartbeats.seen_since(command.actor.timeout)
    last_emitted_ecp = timestamp_to_iso(command.actor._last_emitted_ecp)
    last_emitted_outside = timestamp_to_iso(command.actor._last_emitted_outside)

    heartbeats = {
        hb_name: {
            "current": seen[hb_name],
            "last_seen": timestamp_to_iso(hb.last_set),
        }
        for hb_name, hb in command.actor.heartbeats.items()
    }

    return command.finish(
        heartbeats=heartbeats,
        last_emitted_ecp=last_emitted_ecp,
        last_emitted_outside=last_emitted_outside,
        network=command.actor.network_status,
    )


@command_parser.command()
@click.argument("heartbeat", type=str)
async def set(command: BeatCommand, heartbeat: str):
    """Sets the heartbeat for a component."""

    if heartbeat not in command.actor.heartbeats:
        return command.fail(f"Heartbeat {heartbeat!r} not found.")

    command.actor.heartbeats[heartbeat].set()
    await command.actor.update()

    return command.finish(text="Heartbeat set.")
