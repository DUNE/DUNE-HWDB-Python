#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

#{{{
from Sisyphus.Configuration import config, USER_SETTINGS_DIR
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut

from Sisyphus.Utils.Terminal.Style import Style

from Sisyphus.Gui.Shipping.Widgets import PageWidget, NavBar
from Sisyphus.Gui.Shipping.Widgets import (
            ZLineEdit, ZTextEdit, ZCheckBox, ZDateTimeEdit, ZRadioButtonGroup)

from Sisyphus.Gui.Shipping.ShippingLabel import ShippingLabel

from PyQt5.QtCore import QSize, Qt, pyqtSignal, pyqtSlot, QDateTime
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QStackedLayout,
    QLabel,
    QTextEdit,
    QPlainTextEdit,
    QLineEdit,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QCheckBox,
    QTabWidget,
    QMenu,
    QMenuBar,
    QAction,
    QStackedWidget,
    QRadioButton,
    QGroupBox,
    QButtonGroup,
    QCalendarWidget,
    QDateTimeEdit,
)

import json
#}}}

class PreShipping5(PageWidget):
    #{{{
    page_name = "Pre-Shipping Workflow (5)"
    page_short_name = "Pre-Shipping (5)"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.received_acknowledgement = ZCheckBox("Yes, I have received an acknowledgement",
                    owner=self, key='received_acknowledgement')

        self.acknowledged_by = ZLineEdit(owner=self, key='acknowledged_by')

        self.acknowledged_time = ZDateTimeEdit(owner=self, key='acknowledged_time')

        self.damage_status = ZRadioButtonGroup(owner=self, key='damage_status', default='no damage')
        self.damage_status.create_button('no damage', 'no damage')
        self.damage_status.create_button('damage', 'damage')

        self.damage_description = ZTextEdit(owner=self, key='damage_description')

        self._setup_UI()


    def _setup_UI(self):
        #{{{
        screen_layout = QVBoxLayout()
        ########################################

        page_title = QLabel("Pre-Shipping Workflow (5)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)

        ################

        label1 = QLabel(
                "An email has been sent to the FD Logistics Team."
                "Do not continue until you have received an acknowledgement from them."
        )
        label1.setWordWrap(True)
        screen_layout.addWidget(label1)
        screen_layout.addSpacing(15)


        screen_layout.addWidget(
            QLabel("Have you received an acknowledgement from the FD Logistics team?")
        )

        screen_layout.addWidget(
            self.received_acknowledgement
        )

        screen_layout.addWidget(QLabel("Acknowledged by whom?"))
        screen_layout.addWidget(self.acknowledged_by)

        screen_layout.addWidget(QLabel("When acknowledged (date/time in Central Time)?"))
        screen_layout.addWidget(self.acknowledged_time)

        screen_layout.addSpacing(15)
        screen_layout.addWidget(
            QLabel("Is there any visually obvious damage on the shipment?")
        )

        screen_layout.addWidget(self.damage_status.button('no damage'))
        screen_layout.addWidget(self.damage_status.button('damage'))

        screen_layout.addSpacing(5)
        screen_layout.addWidget(QLabel("If there is damage, describe the damage"))
        screen_layout.addWidget(self.damage_description)





        ################

        screen_layout.addStretch()

        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
        #}}}

    def update(self):
        super().update()

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
    


    #}}}
