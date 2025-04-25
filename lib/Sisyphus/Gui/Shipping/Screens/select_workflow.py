#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

HLD = highlight = "[bg=#999999,fg=#ffffff]"
HLI = highlight = "[bg=#009900,fg=#ffffff]"
HLW = highlight = "[bg=#999900,fg=#ffffff]"
HLE = highlight = "[bg=#990000,fg=#ffffff]"

from Sisyphus.Gui.Shipping import Widgets as zw
from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

import json

class SelectWorkflow(zw.PageWidget):
    page_name = "Select Workflow"
    page_short_name = "Select Workflow"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        

        self.workflow_type = zw.ZRadioButtonGroup(
                        page=self, key='workflow_type', default='preshipping')

        #self.workflow_type.create_button("packing", "Packing")
        self.workflow_type.create_button("preshipping", "Pre-Shipping")
        self.workflow_type.create_button("shipping", "Shipping")
        self.workflow_type.create_button("transit", "Transit")
        self.workflow_type.create_button("receiving", "Receiving")

        self._setup_UI()

    def _setup_UI(self):
        #{{{
        main_layout = qtw.QVBoxLayout()

        #page_title = QLabel("Select Shipping Workflow")
        #page_title.setStyleSheet("""
        #        font-size: 14pt;
        #        font-weight: bold;
        #    """)
        #page_title.setAlignment(Qt.AlignCenter)
        #main_layout.addWidget(page_title)
        main_layout.addWidget(self.title_bar)


        main_layout.addSpacing(20)

        #main_layout.addWidget(self.workflow_type.button("packing"))
        main_layout.addWidget(self.workflow_type.button("preshipping"))
        main_layout.addWidget(self.workflow_type.button("shipping"))
        main_layout.addWidget(self.workflow_type.button("transit"))
        main_layout.addWidget(self.workflow_type.button("receiving"))
        
        main_layout.addStretch()

        #self.nav_bar = self.parent().NavBar(self.parent())

        main_layout.addWidget(self.nav_bar)

        self.setLayout(main_layout)
        #}}}

    def save(self):
        super().save()

    def refresh(self):
        super().refresh()
        if self.page_state.get('workflow_type', None) is not None:
            self.nav_bar.continue_button.setEnabled(True)
        else:
            self.nav_bar.continue_button.setEnabled(False)


    def restore(self):
        super().restore()


