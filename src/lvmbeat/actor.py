#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2024-12-20
# @Filename: actor.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio
from time import time

from typing import Annotated

import click
import httpx
from pydantic import BaseModel, Field

from clu.actor import AMQPActor
from clu.command import Command
from clu.parsers.click import command_parser
from sdsstools import cancel_task

from lvmbeat.heartbeats import HeartbeatData, Heartbeats
from lvmbeat.tools import timestamp_to_iso


class BeatSchema(BaseModel):
    """Reply schema for :obj:`.BeatActor`."""

    heartbeats: Annotated[
        dict[str, bool],
        Field(description="Status of the component heartbeats."),
    ]
    last_emitted: Annotated[
        str | None,
        Field(description="ISO date of the last emitted heartbeat."),
    ]
    last_outside: Annotated[
        str | None,
        Field(
            description="ISO date of the last successful "
            "heartbeat to the outside world."
        ),
    ]


class BeatActor(AMQPActor):
    """Heartbeat actor."""

    parser = command_parser

    def __init__(self, *args, heartbeats: list[HeartbeatData] = [], **kwargs):
        if "schema" not in kwargs:
            kwargs["schema"] = BeatSchema

        super().__init__(*args, **kwargs)

        # Number of seconds after which a heartbeat is considered to be down.
        self.timeout: float = self.config.get("timeout", 30)

        # Create the heartbeats instance. The information is usually passed
        # in the configuration as the heartbeats key.
        heartbeat_data = heartbeats or self.config.get("heartbeats", [])
        self.heartbeats = Heartbeats(heartbeat_data)

        # Track internal status.
        self._last_emitted: float | None = None
        self._last_outside: float | None = None

        self._emit_outside_task = asyncio.create_task(self.emit_outside())

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
                    self.log.warning(f"Heartbeat for {hb_name!r} not seen.")
                    return

        if self._last_emitted and time() - self._last_emitted < 10:
            # Prevent emitting the heartbeat too often.
            return

        self.log.info("Emitting dome heartbeat.")
        cmd = await self.send_command("lvmecp", "heartbeat")
        if not cmd.status.did_succeed:
            self.log.error("Possible error emitting dome heartbeat.")

    async def emit_outside(self):
        """Emits a heartbeat to the outside world."""

        base_url = self.config.get("outside_url")
        if not base_url:
            self.log.warning(
                "No outside URL defined. Will not emit "
                "heartbeats to the outside world."
            )
            return

        while True:
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(base_url)
                    response.raise_for_status()
                except Exception as ee:
                    self.log.error(f"Error emitting heartbeat to {base_url!r}: {ee}")
                else:
                    self.log.debug(f"Emitted heartbeat to {base_url!r}.")
                    self._last_outside = time()

            await asyncio.sleep(15)


BeatCommand = Command[BeatActor]


@command_parser.command()
async def status(command: BeatCommand):
    """Outputs the status of the heartbeats."""

    heartbeats = command.actor.heartbeats.seen_since(command.actor.timeout)
    last_emitted = timestamp_to_iso(command.actor._last_emitted)
    last_outside = timestamp_to_iso(command.actor._last_outside)

    return command.finish(
        heartbeats=heartbeats,
        last_emitted=last_emitted,
        last_outside=last_outside,
    )


@command_parser.command()
@click.argument("heartbeat", type=str)
async def set(command: BeatCommand, heartbeat: str):
    """Sets the heartbeat for a component."""

    if heartbeat not in command.actor.heartbeats:
        return command.fail(f"Heartbeat {heartbeat!r} not found.")

    command.actor.heartbeats[heartbeat].set()
    await command.actor.update()

    return command.finish()
