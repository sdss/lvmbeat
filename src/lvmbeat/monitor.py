#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2024-12-22
# @Filename: monitor.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import os
from dataclasses import dataclass, field

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from lvmopstools.notifications import send_critical_error_email


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


app = FastAPI(swagger_ui_parameters={"tagsSorter": "alpha"})


def email_settings():
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


@app.get("/email/test", description="Sends a test email.")
async def route_get_email_test(
    email_settings: Annotated[EmailSettings, Depends(email_settings)],
):
    """Sends a test email."""

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
        "This is a test message. Please ignore.",
        subject="TEST: LCO internet is down",
        recipients=email_settings.recipients,
        from_address=email_settings.from_address,
        email_reply_to=email_settings.email_reply_to,
        host=email_settings.host,
        port=email_settings.port,
        tls=email_settings.tls,
        username=email_settings.username,
        password=email_settings.password,
    )

    return {"message": "Email sent."}
