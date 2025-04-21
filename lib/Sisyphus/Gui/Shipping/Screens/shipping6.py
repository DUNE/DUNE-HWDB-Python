#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.Gui.Shipping import Widgets as zw

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

###############################################################################

class Shipping6(zw.PageWidget):
    page_name = "Shipping Workflow (6)"
    page_short_name = "Shipping (6)"

    def __init__(self, *args, **kwargs):
        #{{{
        super().__init__(*args, **kwargs)

        self._setup_UI()
        #}}}

    def _setup_UI(self):
        #{{{
        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)

        #############################

        main_layout.addWidget(
            qtw.QLabel("(Optional)\n"
                    "A CSV file [TBD] has been saved in your working directory.\n"
                    "You may wish to email it and other documents to your collaborators."))

        main_layout.addStretch()

        main_layout.addWidget(self.nav_bar)
        self.setLayout(main_layout)
        #}}}

    def refresh(self):
        super().refresh()
        self.nav_bar.continue_button.setText("Finish")
