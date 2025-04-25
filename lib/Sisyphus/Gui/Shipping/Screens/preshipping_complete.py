#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""                                                                                                             Copyright (c) 2025 Regents of the University of Minnesota
Author:                                                                                                             Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.Gui.Shipping import Widgets as zw

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

###############################################################################

class PreShippingComplete(zw.PageWidget):
    page_name = "Pre-Shipping Workflow Complete"
    page_short_name = "Pre-Shipping Complete"
    _warn_before_closing = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._setup_UI()
        self.refresh()
        

    def _setup_UI(self):
        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)

        ########################################

        main_layout.addSpacing(30)

        main_layout.addWidget(
                qtw.QLabel("This workflow is finished. You may close this tab."))


        main_layout.addStretch()

        main_layout.addWidget(self.nav_bar)
        self.nav_bar.set_buttons(['close', 'continue'])
        self.nav_bar.continue_button.setText('Continue to Shipping')

        self.setLayout(main_layout)

    def on_navigate_next(self):
        self.workflow.get_page_by_id("Shipping1").page_state['from_preshipping'] = True
        return super().on_navigate_next()


    def refresh(self):
        super().refresh()

