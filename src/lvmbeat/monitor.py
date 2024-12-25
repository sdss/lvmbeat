#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2024-12-22
# @Filename: monitor.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import fastapi_utils
import fastapi_utils.tasks
from fastapi import FastAPI, HTTPException
from fastapi.datastructures import State
from lvmopstools.notifications import send_critical_error_email

from lvmbeat import __version__, config


logger = logging.getLogger("uvicorn.error")


@dataclass
class EmailSettings:
    """A class to store the state of the monitor webapp."""

    recipients: list[str] = field(default_factory=list)
    from_address: str | None = None
    email_reply_to: str | None = None
    host: str | None = None
    port: int | None = None
    tls: bool = False
    username: str | None = None
    password: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles the application life-cycle."""

    await check_heartbeat()

    yield


app = FastAPI(swagger_ui_parameters={"tagsSorter": "alpha"}, lifespan=lifespan)
app.state = State(
    {
        "active": False,
        "last_seen": time.time(),
        "enabled": True,
    }
)


def get_email_settings():
    """Returns the email settings reading from environment variables."""

    recipients_envvar = os.getenv("LVMBEAT_EMAIL_RECIPIENTS", [])
    if isinstance(recipients_envvar, str):
        recipients = recipients_envvar.split(",")
    else:
        recipients = []

    from_address = os.getenv("LVMBEAT_EMAIL_FROM_ADDRESS")
    email_reply_to = os.getenv("LVMBEAT_EMAIL_REPLY_TO")
    host = os.getenv("LVMBEAT_EMAIL_HOST")

    port_envvar = os.getenv("LVMBEAT_EMAIL_PORT")
    port = int(port_envvar) if port_envvar else None

    tls = os.getenv("LVMBEAT_EMAIL_TLS")
    if tls and (tls is True or tls.lower() in ["true", "yes", "1"]):
        tls = True
    else:
        tls = False

    username = os.getenv("LVMBEAT_EMAIL_USERNAME")
    password = os.getenv("LVMBEAT_EMAIL_PASSWORD")

    return EmailSettings(
        recipients=recipients,
        from_address=from_address,
        email_reply_to=email_reply_to or from_address,
        host=host,
        port=port,
        tls=tls,
        username=username,
        password=password,
    )


def send_email(message: str, subject: str):
    """Sends a critical alert email notification."""

    email_settings = get_email_settings()

    if len(email_settings.recipients) == 0:
        raise HTTPException(status_code=400, detail="No recipients defined.")
    if email_settings.from_address is None:
        raise HTTPException(status_code=400, detail="No from_address defined.")
    if email_settings.host is None:
        raise HTTPException(status_code=400, detail="No host defined.")
    if email_settings.port is None:
        raise HTTPException(status_code=400, detail="No port defined.")
    if email_settings.tls:
        if email_settings.username is None:
            raise HTTPException(status_code=400, detail="No username defined.")
        if email_settings.password is None:
            raise HTTPException(status_code=400, detail="No password defined.")

    send_critical_error_email(
        message=message,
        subject=subject,
        recipients=email_settings.recipients,
        from_address=email_settings.from_address,
        email_reply_to=email_settings.email_reply_to,
        host=email_settings.host,
        port=email_settings.port,
        tls=email_settings.tls,
        username=email_settings.username,
        password=email_settings.password,
    )


@fastapi_utils.tasks.repeat_every(seconds=20, logger=logger, raise_exceptions=False)
def check_heartbeat():
    """Checks if we have received a heartbeat from LCO or sends an alert."""

    logger.debug("Checking heartbeat.")

    if not app.state.enabled:
        logger.debug("Heartbeat monitor is disabled.")
        return

    max_time_to_alert: float = float(
        os.getenv(
            "LVMBEAT_SEND_EMAIL_AFTER",
            config["outside_monitor.send_email_after"],
        )
    )

    now = time.time()
    if not app.state.active and now - app.state.last_seen > max_time_to_alert:
        logger.warning(
            f"No heartbeat received in the last {max_time_to_alert} seconds. "
            "Sending critical alert email."
        )
        send_email(
            message="The LCO internet connection is down.",
            subject="LCO internet is down",
        )
        app.state.active = True

    elif app.state.active and now - app.state.last_seen < max_time_to_alert:
        logger.info("Heartbeat received. Resetting alert and sending all-clear email.")
        send_email(
            message="The LCO internet connection appears to be up.",
            subject="RESOLVED: LCO internet is up",
        )
        app.state.active = False


@app.get("/heartbeat", description="Sets the heartbeat.")
def route_get_heartbeat():
    """Sets the heartbeat."""

    app.state.last_seen = time.time()

    return {"message": "Heartbeat received."}


@app.get("/heartbeat/status", description="Status of the heartbeat monitor.")
def route_get_heartbeat_status():
    """Status of the heartbeat monitor."""

    return {
        "enabled": app.state.enabled,
        "active": app.state.active,
        "last_seen": app.state.last_seen,
    }


@app.get("/heartbeat/enable", description="Enables the heartbeat monitor.")
def route_get_heartbeat_enable():
    """Enables the heartbeat monitor."""

    app.state.enabled = True

    return {"message": "Heartbeat monitor enabled."}


@app.get("/heartbeat/disable", description="Disables the heartbeat monitor.")
def route_get_heartbeat_disable():
    """Disables the heartbeat monitor."""

    app.state.enabled = False

    return {"message": "Heartbeat monitor disabled."}


@app.get("/email/test", description="Sends a test email.")
def route_get_email_test():
    """Sends a test email."""

    send_email("This is a test message. Please ignore.", "TEST: LCO internet is down")

    return {"message": "Email sent."}


@app.get("/version", description="Returns the version of the monitor.")
def route_get_version():
    """Returns the version of the monitor."""

    return {"version": __version__}
