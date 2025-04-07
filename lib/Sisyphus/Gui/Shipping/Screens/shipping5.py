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

HLD = highlight = "[bg=#999999,fg=#ffffff]"
HLI = highlight = "[bg=#009900,fg=#ffffff]"
HLW = highlight = "[bg=#999900,fg=#ffffff]"
HLE = highlight = "[bg=#990000,fg=#ffffff]"

class Shipping5(zw.PageWidget):
    page_name = "Shipping Workflow (5)"
    page_short_name = "Shipping (5)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.select_location = zw.ZInstitutionWidget(owner=self, key='location')        
        #self.select_location = zw.ZLineEdit(owner=self, key='location')        

        self._setup_UI()

    def _setup_UI(self):
        #{{{
        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)        

        ########################################

        main_layout.addWidget(self.select_location)

 
        ################

        main_layout.addStretch()
        main_layout.addWidget(self.nav_bar)
        self.setLayout(main_layout)
        #}}}














