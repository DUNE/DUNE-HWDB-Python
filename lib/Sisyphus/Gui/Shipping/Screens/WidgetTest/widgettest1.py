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
from Sisyphus.Gui.Shipping.Widgets.PageWidget import PageWidget
from Sisyphus.Gui.Shipping.Tasks import Database as dbt
from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

###############################################################################

class WidgetTest1(PageWidget):
    page_name = "Widget Test (1)"
    page_short_name = "Widget Test"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.location_history = zw.ZLocationHistory(page=self, 
                            key='location_history', source='workflow:part_info')

        self.new_location = zw.ZInstitutionWidget(
                            page=self, key='location', source='application:attr:locations')        
        self.arrival_time = zw.ZDateTimeEdit(page=self, key='arrived')
        self.comments = zw.ZLineEdit(page=self, key='comments')
        self.affirm_update = zw.ZCheckBox(page=self, 
                        text="Yes, update the location now", key='affirm_update')

        self._setup_UI()

    def _setup_UI(self):
        #{{{
        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)        

        ########################################

        main_layout.addWidget(self.location_history)

        main_layout.addWidget(
            qtw.QLabel("Please update the Location record for this shipment."))
        main_layout.addSpacing(15)

        main_layout.addWidget(
            qtw.QLabel("Location"))
        main_layout.addWidget(self.new_location)
        main_layout.addSpacing(15)

        main_layout.addWidget(
            qtw.QLabel("Date/Time (Central time zone)"))
        main_layout.addWidget(self.arrival_time)
        main_layout.addSpacing(15)
        
        main_layout.addWidget(
            qtw.QLabel("Comments"))
        main_layout.addWidget(self.comments)
        main_layout.addSpacing(35)


        main_layout.addWidget(
            qtw.QLabel("Do you wish to update the location?"))
        main_layout.addWidget(self.affirm_update)

        ################

        main_layout.addStretch()
        main_layout.addWidget(self.nav_bar)
        self.setLayout(main_layout)
        #}}}

    def refresh(self):
        #{{{
        super().refresh()

        if not self.new_location.institution_id:
            self.nav_bar.continue_button.setEnabled(False)
            return

        if not self.affirm_update.isChecked():
            self.nav_bar.continue_button.setEnabled(False)
            return

        self.nav_bar.continue_button.setEnabled(True)
        #}}}

    def update_location(self):
        with self.wait():
            ok = dbt.update_location(
                            part_id=self.part_id, 
                            location=self.page_state["location"]['institution_id'],
                            arrived=self.page_state["arrived"],
                            comments=self.page_state["comments"])
        return True

    def on_navigate_next(self):
        super().on_navigate_next()
        ok = self.update_location()
        return ok










