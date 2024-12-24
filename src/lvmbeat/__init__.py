#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2024-12-23
# @Filename: __init__.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import pathlib

from sdsstools import get_config, get_package_version


# pip package name
NAME = "sdss-lvmecp"

# Loads config. config name is the package name.
config = get_config(
    "lvmbeat",
    config_file=pathlib.Path(__file__).parent / "config.yaml",
)


# package name should be pip package name
__version__ = get_package_version(path=__file__, package_name=NAME)
