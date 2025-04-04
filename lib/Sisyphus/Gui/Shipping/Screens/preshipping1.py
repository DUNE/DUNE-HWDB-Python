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
#}}}

class PreShipping1(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_name = "Pre-Shipping (1)"

        # Create the interactive widgets on this page

        self.subcomp_caption = QLabel("Contents")

        self.table = QTableWidget(0, 3)
        self.table.verticalHeader().setVisible(False)

        msg = "The list of components for this shipment is correct"
        self.confirm_list_checkbox = ZCheckBox(owner=self, text=msg, key="confirm_list")
        #self.confirm_list_checkbox.toggled.connect(self.toggle_confirm_list)
        

        msg = "All necessary QA/QC information for these components " \
                    "has been stored in the HWDB"
        self.confirm_hwdb_updated_checkbox = ZCheckBox(owner=self, text=msg, key="hwdb_updated")
        #self.confirm_hwdb_updated_checkbox.toggled.connect(self.toggle_hwdb_updated)
        
        # Create the actual layout and place the interactive widgets in it
        self._construct_page()

    def _construct_page(self):
        #{{{
        # This should create the visual appearance of the page. Any widgets
        # that are interactive should be created elsewhere, and then placed
        # inside the layout here. The reason for doing it this way is so
        # that the code creating and controlling dynamic elements won't be
        # cluttered by all the layout code here.

        screen_layout = QVBoxLayout()

        ########################################

        page_title = QLabel("Pre-Shipping Workflow (1)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        
        ########################################

        subcomp_list_layout = QVBoxLayout()
        subcomp_list_layout.addWidget( self.subcomp_caption )
        subcomp_list_layout.addSpacing(5)
        horizontal_header = self.table.horizontalHeader()
        horizontal_header.resizeSection(0, 200)
        horizontal_header.resizeSection(1, 275)
        horizontal_header.resizeSection(2, 275)
        self.table.setHorizontalHeaderLabels(['Sub-component PID',
                            'Component Type Name', 'Functional Position Name'])
        subcomp_list_layout.addWidget(self.table)
        subcomp_list_widget = QWidget()
        subcomp_list_widget.setLayout(subcomp_list_layout)
        screen_layout.addWidget(subcomp_list_widget)
        screen_layout.addSpacing(10)

        ########################################


        screen_layout.addWidget(QLabel("Please affirm the following:"))

        affirm_layout = QHBoxLayout()
        affirm_layout.addSpacing(10)

        indented_layout = QVBoxLayout()
        indented_layout.addWidget(self.confirm_list_checkbox)
        indented_layout.addWidget(self.confirm_hwdb_updated_checkbox)
        indented_widget = QWidget()
        indented_widget.setLayout(indented_layout)
        affirm_layout.addWidget(indented_widget)
        affirm_widget = QWidget()
        affirm_widget.setLayout(affirm_layout)
        screen_layout.addWidget(affirm_widget)

        ########################################

        screen_layout.addStretch()

        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
        #}}}

    def restore(self):
        super().restore()
        self.populate_subcomps()

    def populate_subcomps(self):

        if self.tab_state.get('part_info', None) is None:
            subcomps = {}

        else:
            subcomps = self.tab_state['part_info'].setdefault('subcomponents', {})

        self.table.setRowCount(len(subcomps))
        for idx, subcomp in enumerate(subcomps.values()):
            self.table.setItem(idx, 0, QTableWidgetItem(subcomp['Sub-component PID']))
            self.table.setItem(idx, 1, QTableWidgetItem(subcomp['Component Type Name']))
            self.table.setItem(idx, 2, QTableWidgetItem(subcomp['Functional Position Name']))
    
    def update(self):
        super().update()

        if (self.page_state.get('confirm_list', False) 
                    and self.page_state.get('hwdb_updated', False)):
            self.nav_bar.continue_button.setEnabled(True)
        else:
            self.nav_bar.continue_button.setEnabled(False)

    #}}}

