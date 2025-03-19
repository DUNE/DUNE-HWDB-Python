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

from Sisyphus.Gui.Shipping.Widgets import PageWidget
from Sisyphus.Gui.Shipping.Widgets import ZLineEdit, ZTextEdit, ZCheckBox, ZDateTimeEdit

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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.received_acknowledgement = ZCheckBox("Yes, I have received an acknowledgement",
                    parent=self, key='received_acknowledgement')

        self.acknowledged_by = ZLineEdit(parent=self, key='acknowledged_by')

        #self.acknowledged_time = QCalendarWidget()
        self.acknowledged_time = ZDateTimeEdit(parent=self, key='acknowledged_time')
        #self.acknowledged_time.setCalendarPopup(True)

        self.radio_no_damage = QRadioButton("No obvious damage to report")
        self.radio_damage = QRadioButton("There is some damage")
        self.radio_no_damage.toggled.connect(self.select_damage_status)
        self.radio_damage.toggled.connect(self.select_damage_status)

        self.damage_description = ZTextEdit(parent=self, key='damage_description')

        self._construct_page()

    def select_damage_status(self):
        rb = self.sender()
        if not rb.isChecked():
            return

        if rb is self.radio_no_damage:
            self.page_state['damage_status'] = 'no damage'
        elif rb is self.radio_damage:
            self.page_state['damage'] = 'damage'

        self.save()

    def restore(self):
        super().restore()

        damage_status = self.page_state.setdefault('damage_status', 'no damage')

        if damage_status == 'damage':
            self.radio_damage.setChecked(True)
        else:
            self.radio_no_damage.setChecked(True)


    def _construct_page(self):
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

        screen_layout.addWidget(self.radio_no_damage)
        screen_layout.addWidget(self.radio_damage)

        screen_layout.addSpacing(5)
        screen_layout.addWidget(QLabel("If there is damage, describe the damage"))
        screen_layout.addWidget(self.damage_description)





        ################

        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
    #}}}
