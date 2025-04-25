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

class PreShipping6(zw.PageWidget):
    page_name = "Pre-Shipping Workflow (6)"
    page_short_name = "Pre-Shipping (6)"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.received_acknowledgement = zw.ZCheckBox("Yes, I have received an acknowledgement",
                    page=self, key='received_acknowledgement')

        self.acknowledged_by = zw.ZLineEdit(page=self, key='acknowledged_by')

        self.acknowledged_time = zw.ZDateTimeEdit(page=self, key='acknowledged_time')

        self.damage_status = zw.ZRadioButtonGroup(page=self, key='damage_status', default='no damage')
        self.damage_status.create_button('no damage', 'no damage')
        self.damage_status.create_button('damage', 'damage')

        self.damage_description = zw.ZTextEdit(page=self, key='damage_description')

        self._setup_UI()


    def _setup_UI(self):
        #{{{
        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)

        ########################################

        label1 = qtw.QLabel(
                "An email has been sent to the FD Logistics Team."
                "Do not continue until you have received an acknowledgement from them."
        )
        label1.setWordWrap(True)
        main_layout.addWidget(label1)
        main_layout.addSpacing(15)


        main_layout.addWidget(
            qtw.QLabel("Have you received an acknowledgement from the FD Logistics team?")
        )

        main_layout.addWidget(
            self.received_acknowledgement
        )

        main_layout.addWidget(qtw.QLabel("Acknowledged by whom?"))
        main_layout.addWidget(self.acknowledged_by)

        main_layout.addWidget(qtw.QLabel("When acknowledged (date/time in Central Time)?"))
        main_layout.addWidget(self.acknowledged_time)

        main_layout.addSpacing(15)
        main_layout.addWidget(
            qtw.QLabel("Is there any visually obvious damage on the shipment?")
        )

        main_layout.addWidget(self.damage_status.button('no damage'))
        main_layout.addWidget(self.damage_status.button('damage'))

        main_layout.addSpacing(5)
        main_layout.addWidget(qtw.QLabel("If there is damage, describe the damage"))
        main_layout.addWidget(self.damage_description)

        ################

        main_layout.addStretch()

        main_layout.addWidget(self.nav_bar)

        self.setLayout(main_layout)
        #}}}

    def refresh(self):
        super().refresh()

        if self.page_state.get('damage_status', None) == 'no damage':
            self.damage_description.setEnabled(False)
        else:
            self.damage_description.setEnabled(True)

        if not self.received_acknowledgement.isChecked():
            self.nav_bar.continue_button.setEnabled(False)
            return

        if len(self.acknowledged_by.text()) == 0:
            self.nav_bar.continue_button.setEnabled(False)
            return

        if (self.page_state.get('damage_status', None) == 'damage' 
                and len(self.page_state.get('damage_description', '')) == 0):
            self.nav_bar.continue_button.setEnabled(False)
            
        self.nav_bar.continue_button.setEnabled(True)
    


