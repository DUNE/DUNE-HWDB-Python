#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.Gui.Configuration import ConfigDialog
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc

# Mute the super-annoying "qt.xkb.compose: failed to create compose table"
# message that QT seems to spit out all the time.
qtc.QLoggingCategory.setFilterRules("qt.xkb.compose.warning=false")

import qdarkstyle
import sys

def main(args):
    app = qtw.QApplication(args)

    dark_stylesheet = qdarkstyle.load_stylesheet_pyqt5()
    app.setStyleSheet(dark_stylesheet)

    config_dialog = ConfigDialog()
    config_dialog.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
