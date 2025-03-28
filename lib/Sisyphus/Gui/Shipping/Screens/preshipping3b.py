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
from Sisyphus.Gui.Shipping.Widgets import ZLineEdit, ZTextEdit, ZCheckBox, ZDateTimeEdit

from Sisyphus.Gui.Shipping.ShippingLabel import ShippingLabel

from PyQt5.QtCore import QSize, Qt, pyqtSignal, pyqtSlot
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
)

import json
#}}}

class PreShipping3b(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.freight_forwarder = ZLineEdit(owner=self, key='freight_forwarder')
        self.mode_of_transportation = ZLineEdit(owner=self, key='mode_of_transportation')
        #self.expected_arrival_time = ZLineEdit(owner=self, key='expected_arrival_time')
        self.expected_arrival_time = ZDateTimeEdit(owner=self, key='expected_arrival_time')
        

        self._construct_page()

    def _construct_page(self):
        #{{{
        screen_layout = QVBoxLayout()
        ########################################

        page_title = QLabel("Pre-Shipping Workflow (3b)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        ################
        ################

        ff_label = QLabel(
                "Provide name(s) of your Freight Forwarder (FF; such as FedEx or UPS. "
                "USPS is not allowed) and mode(s) of transportation (truck, air, ship, "
                "rail, etc.):"
        )
        ff_label.setWordWrap(True)
        screen_layout.addWidget(ff_label)

        ff_mode_layout = QVBoxLayout()

        ff_layout = QHBoxLayout()
        ff_layout.addWidget( QLabel("Name of FF:") )
        ff_layout.addWidget( self.freight_forwarder )
        ff_widget = QWidget()
        ff_widget.setLayout(ff_layout)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget( QLabel("Mode:") )
        mode_layout.addWidget( self.mode_of_transportation )
        mode_widget = QWidget()
        mode_widget.setLayout(mode_layout)

        ff_mode_layout.addWidget(ff_widget)
        ff_mode_layout.addWidget(mode_widget)
        ff_mode_widget = QWidget()
        ff_mode_widget.setLayout(ff_mode_layout)

        screen_layout.addWidget(ff_mode_widget)

        ################

        screen_layout.addSpacing(10)



        screen_layout.addWidget(QLabel("Provide the expected arrival time (Central Time):"))
        screen_layout.addWidget( self.expected_arrival_time)


        ################

        screen_layout.addStretch()

        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
        #}}}

    def update(self):
        super().update()
        
        if (
                len(self.freight_forwarder.text()) > 0
                and len(self.mode_of_transportation.text()) > 0):
            self.nav_bar.continue_button.setEnabled(True)
        else:
            self.nav_bar.continue_button.setEnabled(False)


    #}}}
