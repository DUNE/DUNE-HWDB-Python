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
from Sisyphus.Gui.Shipping import Model as mdl
from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

HLD = highlight = "[bg=#999999,fg=#ffffff]"
HLI = highlight = "[bg=#009900,fg=#ffffff]"
HLW = highlight = "[bg=#999900,fg=#ffffff]"
HLE = highlight = "[bg=#990000,fg=#ffffff]"

###############################################################################

class Shipping5(zw.PageWidget):
    page_name = "Shipping Workflow (5)"
    page_short_name = "Shipping (5)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.shipping_location = zw.ZInstitutionWidget(owner=self, key='location')        
        self.shipping_time = zw.ZDateTimeEdit(owner=self, key='shipment_time')
        self.comments = zw.ZLineEdit(owner=self, key='comments')
        self.affirm_shipment = zw.ZCheckBox(owner=self, 
                        text="I have shipped the cargo", key='affirm_shipment')

        self._setup_UI()

    def _setup_UI(self):
        #{{{
        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)        

        ########################################

        main_layout.addWidget(
            qtw.QLabel("Please update the Location record for this shipment."))
        main_layout.addSpacing(15)

        main_layout.addWidget(
            qtw.QLabel("Location"))
        main_layout.addWidget(self.shipping_location)
        main_layout.addSpacing(15)

        main_layout.addWidget(
            qtw.QLabel("Date/Time (Central time zone)"))
        main_layout.addWidget(self.shipping_time)
        main_layout.addSpacing(15)
        
        main_layout.addWidget(
            qtw.QLabel("Comments"))
        main_layout.addWidget(self.comments)
        main_layout.addSpacing(35)


        main_layout.addWidget(
            qtw.QLabel("You may now ship your cargo!"))
        main_layout.addWidget(self.affirm_shipment)

        ################

        main_layout.addStretch()
        main_layout.addWidget(self.nav_bar)
        self.setLayout(main_layout)
        #}}}

    def update(self):
        #{{{
        super().update()

        if not self.shipping_location.institution_id:
            self.nav_bar.continue_button.setEnabled(False)
            return

        if not self.affirm_shipment.isChecked():
            self.nav_bar.continue_button.setEnabled(False)
            return

        self.nav_bar.continue_button.setEnabled(True)
        #}}}

    def update_location(self):
        ok = mdl.update_location(
                        part_id=self.part_id, 
                        location=self.page_state["location"],
                        arrived=self.page_state["shipment_time"],
                        comments=self.page_state["comments"])
        return True

    def on_navigate_next(self):
        super().on_navigate_next()
        ok = self.update_location()
        return ok










