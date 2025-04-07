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
from Sisyphus.Gui.Shipping.Widgets import ZLineEdit, ZTextEdit, ZCheckBox, ZRadioButtonGroup

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

class PreShipping3a(PageWidget):
    #{{{
    page_name = "Pre-Shipping Workflow (3a)"
    page_short_name = "Pre-Shipping (3a)"

    def __init__(self, *args, **kwargs):
        #{{{
        super().__init__(*args, **kwargs)

        self.destination_type = ZRadioButtonGroup(
                owner=self, key='shipping_service_type', default='Domestic')
        self.destination_type.create_button("Domestic", "Domestic")
        self.destination_type.create_button("International", "International")

        
        self.hts_code = ZLineEdit(owner=self, key='hts_code')
        
        self.shipment_origin = ZLineEdit(owner=self, key='shipment_origin')
        self.dimension = ZLineEdit(owner=self, key='dimension')
        self.weight = ZLineEdit(owner=self, key='weight')

        self._setup_UI()
        #}}}

    def _setup_UI(self):
        #{{{
        screen_layout = QVBoxLayout()
        ########################################

        page_title = QLabel("Pre-Shipping Workflow (3)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        ################


        group_box_1 = QGroupBox()

        group_box_1_layout = QVBoxLayout()
        group_box_1_layout.addWidget(
            QLabel("Will this be a domestic or international shipment?")
        )


        '''
        group_box_1_layout.addWidget(self.radio_domestic)
        group_box_1_layout.addWidget(self.radio_international)
        '''
        group_box_1_layout.addWidget(self.destination_type.button('Domestic'))       
        group_box_1_layout.addWidget(self.destination_type.button('International'))       

        group_box_2 = QGroupBox()
        group_box_2_layout = QVBoxLayout() 
        intl_label_1 = QLabel("For international shipment:")
        intl_label_2 = QLabel(
                "Provide your Harmonized Tariff Schedule (HTS) code.\n"
                " - Use the HTS code that your institution or lab used in the past successfully\n"
                " - Else, for Equipment and Materials for the LBNF & DUNE Scientific Projects, "
                    "use 8543.90.8845 (parts of particle accelerators"
        )
        intl_label_2.setWordWrap(True)
        intl_label_2.setStyleSheet("""
                font-size: 10pt;
            """)
        group_box_2_layout.addWidget(intl_label_1)
        group_box_2_layout.addWidget(intl_label_2)
        group_box_2_layout.addWidget(self.hts_code)
        group_box_2.setLayout(group_box_2_layout)
    
        group_box_1_layout.addWidget(group_box_2)
    
        group_box_1.setLayout(group_box_1_layout)

        screen_layout.addWidget(group_box_1)

        ################
        ################

        screen_layout.addWidget(QLabel("Provide the shipment's origin:"))
        screen_layout.addWidget(self.shipment_origin)

        ################


        dim_wt_label = QLabel(
                "Provide the dimension (length x width x height) and weight of your shipment. "
                "Don't forget to provide their units as well (inches, m, lbs, kg, etc.)"
        )
        dim_wt_label.setWordWrap(True)
        screen_layout.addWidget(dim_wt_label)

        dim_wt_layout = QVBoxLayout()

        dim_layout = QHBoxLayout()
        dim_layout.addWidget(QLabel("Dimension"))
        dim_layout.addWidget(self.dimension)
        dim_widget = QWidget()
        dim_widget.setLayout(dim_layout)

        wt_layout = QHBoxLayout()
        wt_layout.addWidget(QLabel("Weight"))
        wt_layout.addWidget(self.weight)
        wt_widget = QWidget()
        wt_widget.setLayout(wt_layout)

        dim_wt_layout.addWidget(dim_widget)
        dim_wt_layout.addWidget(wt_widget)
        dim_wt_widget = QWidget()
        dim_wt_widget.setLayout(dim_wt_layout)
        screen_layout.addWidget(dim_wt_widget)

        ################
        ################

        screen_layout.addStretch()

        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
        #}}}

    def update(self):
        super().update()

        if self.page_state.get('shipping_service_type', None) == 'International':
            self.hts_code.setEnabled(True)
            if len(self.hts_code.text()) > 0:
                self.nav_bar.continue_button.setEnabled(False)
                return
        else:
            self.hts_code.setEnabled(False)

        if (
                len(self.shipment_origin.text()) > 0
                and len(self.dimension.text()) > 0
                and len(self.weight.text()) > 0 ):
            self.nav_bar.continue_button.setEnabled(True)
        else:
            self.nav_bar.continue_button.setEnabled(False)
    

    #}}}
