#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/HWDBUtility/exceptions.py
Copyright (c) 2024 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""


class HWDBUtilityError(Exception):
    """Base class for HWDBUtility exceptions."""


class InvalidEncoder(HWDBUtilityError):
    """The Encoder has bad or missing information"""

