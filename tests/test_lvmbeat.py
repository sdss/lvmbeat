#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2024-12-22
# @Filename: test_lvmbeat.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from lvmbeat.tools import timestamp_to_iso


def test_timestamp_to_iso():
    assert timestamp_to_iso(1640198400) == "2021-12-22T18:40:00Z"
