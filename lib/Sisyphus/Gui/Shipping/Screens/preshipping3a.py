#!/usr/bin/env python

from Sisyphus.Configuration import config, USER_SETTINGS_DIR
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut

from Sisyphus.Utils.Terminal.Style import Style

from Sisyphus.Gui.Shipping.Widgets import PageWidget
from Sisyphus.Gui.Shipping.Widgets import ZLineEdit, ZTextEdit, ZCheckBox

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

class PreShipping3a(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.radio_domestic = QRadioButton("Domestic")
        self.radio_international = QRadioButton("International")

        self.radio_domestic.toggled.connect(self.select_shipping_service_type)
        self.radio_international.toggled.connect(self.select_shipping_service_type)

        self.hts_code = ZLineEdit(parent=self, key='hts_code')
        
        self.shipment_origin = ZLineEdit(parent=self, key='shipment_origin')
        self.dimension = ZLineEdit(parent=self, key='dimension')
        self.weight = ZLineEdit(parent=self, key='weight')

        self._construct_page()

    def select_shipping_service_type(self):
        rb = self.sender()
        if not rb.isChecked():
            return

        if rb is self.radio_domestic:
            self.page_state['shipping_service_type'] = 'Domestic'
        elif rb is self.radio_international:
            self.page_state['shipping_service_type'] = 'International'

        self.save()
    
    def restore(self):
        shipping_service_type = self.page_state.setdefault('shipping_service_type', 'Domestic')

        if shipping_service_type == 'International':
            self.radio_international.setChecked(True)
        else:
            self.radio_domestic.setChecked(True)
        


    def _construct_page(self):
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



        group_box_1_layout.addWidget(self.radio_domestic)
        group_box_1_layout.addWidget(self.radio_international)
       
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

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
        #}}}
    #}}}
