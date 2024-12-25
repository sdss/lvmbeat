#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2024-12-23
# @Filename: __main__.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import os
from copy import deepcopy

import click
from click_default_group import DefaultGroup

from sdsstools import Configuration
from sdsstools.daemonizer import DaemonGroup, cli_coro

from lvmbeat import config
from lvmbeat.actor import BeatActor


@click.group(cls=DefaultGroup, default="actor", default_if_no_args=True)
@click.option(
    "-c",
    "--config",
    "config_file",
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the user configuration file.",
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Debug mode. Use additional v for more details.",
)
@click.pass_context
def lvmbeat(ctx, verbose, config_file: str | None):
    """Heartbeat middleware and internet connection status."""

    ctx.obj = {
        "verbose": verbose,
        "config_file": config_file,
    }


@lvmbeat.group(cls=DaemonGroup, prog="beat-actor", workdir=os.getcwd())
@click.option(
    "--with-simulator",
    is_flag=True,
    help="Runs the actor aginst the simulator.",
)
@click.pass_context
@cli_coro()
async def actor(ctx, with_simulator: bool = False):
    """Runs the actor."""

    cli_config_file = ctx.obj["config_file"]
    if cli_config_file:
        beat_config = Configuration(cli_config_file, base_config=config)
        print(f"Using config file {cli_config_file}")
    else:
        beat_config = deepcopy(config)
        print("Using internal configuration.")

    actor_obj = BeatActor.from_config(beat_config)
    config.update(beat_config)

    await actor_obj.start()
    await actor_obj.run_forever()


def main():
    lvmbeat(auto_envvar_prefix="LVMBEAT")


if __name__ == "__main__":
    main()
