#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

import sys, os

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus.Gui import DataModel as dm
from Sisyphus.Gui.Shipping.Application import Application

from PyQt5 import QtCore as qtc

# Mute the super-annoying "qt.xkb.compose: failed to create compose table"
# message that QT seems to spit out all the time.
qtc.QLoggingCategory.setFilterRules("qt.xkb.compose.warning=false")


def main(argv):

    sys.argv = argv

    logger.info("Starting Shipping Application")
    Style.info.print("The program is starting up. This may take a moment...")
    
    # Preload data so there won't be a delay later
    # (we don't need to hold the object; the data will
    # be cached so the next time the object is created,
    # it won't need to call the REST API again.)
    _ = dm.Institutions()
    _ = dm.WhoAmI()

    app = Application(sys.argv)

    app.main_window.show()

    print("entering event loop -- window should show in a few seconds")
    print("(On WSL/Ubuntu under Windows, this sometimes takes a minute on the first run.\n"
            "Occasionally, it will not show at all, in which case, you may need to restart\n"
            "WSL. Other Linux setups may have different behaviors.)")

    logger.info("Entering event loop")
    rc = app.exec()
    logger.info("Exiting event loop")

    logger.info("Exiting Shipping Application")
    Style.info.print("Exiting program")

    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv))



