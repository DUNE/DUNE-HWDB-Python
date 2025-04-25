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

class ShippingComplete(zw.PageWidget):

    page_name = "Shipping Workflow Complete"
    page_short_name = "Shipping Complete"
    _warn_before_closing = False

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

        main_layout.addStretch()

        main_layout.addWidget(self.nav_bar)
        
        self.nav_bar.set_buttons(['close'])
        
        self.setLayout(main_layout)
        #}}}

    def refresh(self):
        super().refresh()
        self.nav_bar.back_button.setEnabled(False)
        self.nav_bar.continue_button.setEnabled(False)
