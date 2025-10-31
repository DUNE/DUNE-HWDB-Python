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

class Shipping5(PageWidget):
    page_name = "Shipping Workflow (5)"
    page_short_name = "Shipping (5)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.shipping_location = zw.ZInstitutionWidget(page=self, 
                        key='location', source="application:attr:locations")
        self.shipping_time = zw.ZDateTimeEdit(page=self, key='shipment_time')
        self.comments = zw.ZLineEdit(page=self, key='comments')
        self.affirm_shipment = zw.ZCheckBox(page=self, 
                        text="I have shipped the cargo", key='affirm_shipment')

        self._setup_UI()

    def _setup_UI(self):
        #{{{
        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)        

        ########################################

        
        #locmess = qtw.QLabel("Please update the Location record for this shipment.")
        locmess = qtw.QLabel("The Location has been preselected to be \"In-Transit\".")

        
        main_layout.addWidget(locmess)
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

    def refresh(self):
        #{{{
        super().refresh()

        # --- dynamically update destination based on SelectPID state ---
        #select_pid_state = self.workflow_state.get("SelectPID", {})
        #is_surf = select_pid_state.get("confirm_surf", False)


        #if is_surf:
        self.preselect_institution()
        #print(f"self.part_id = {self.part_id} : self.page_state['location']['institution_id'] = {self.page_state['location']['institution_id']}")


        # The location is now preset (In-Transit)
        #if not self.shipping_location.institution_id:
        #    self.nav_bar.continue_button.setEnabled(False)
        #    return

        if not self.affirm_shipment.isChecked():
            self.nav_bar.continue_button.setEnabled(False)
            return

        self.nav_bar.continue_button.setEnabled(True)
        #}}}

    def update_location(self):
        with self.wait():
            ok = dbt.update_location(
                            part_id=self.part_id, 
                            location=self.page_state["location"]['institution_id'],
                            arrived=self.page_state["shipment_time"],
                            comments=self.page_state["comments"])
        return True

    def on_navigate_next(self):
        super().on_navigate_next()
        ok = self.update_location()
        return ok

    def preselect_institution(self):
        #target_country_code = "US"
        #target_institution_id = 186

        target_country_code = "--" # In-Transit
        target_institution_id = 0  # In-Transit

        loc = self.shipping_location

        # Block signals to prevent recursive refresh
        loc.country_widget.blockSignals(True)
        loc.inst_widget.blockSignals(True)

        # Prevent refresh loop
        old_refresh = loc.page.refresh
        loc.page.refresh = lambda *a, **k: None

        # Now set values safely
        loc.country_code = target_country_code
        loc.institution_id = target_institution_id
        loc.institution_name = loc.institutions[target_institution_id]["name"]

        c_index = loc.country_widget.findData(target_country_code)
        loc.country_widget.setCurrentIndex(c_index)
        loc.on_selectCountry()
        i_index = loc.inst_widget.findData(target_institution_id)
        loc.inst_widget.setCurrentIndex(i_index)

        loc.stored_value = {
            "institution_id": target_institution_id,
            "institution_name": loc.institution_name,
            "country_code": target_country_code,
        }
        self.page_state["location"] = loc.stored_value

        # Restore everything
        loc.page.refresh = old_refresh
        loc.country_widget.blockSignals(False)
        loc.inst_widget.blockSignals(False)

        # Optional: manual refresh if needed
        #self.refresh()
