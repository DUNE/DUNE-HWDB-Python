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

from Sisyphus.Gui.Shipping.Widgets import PageWidget, NavBar
from Sisyphus.Gui.Shipping.Widgets import ZLineEdit, ZTextEdit, ZCheckBox, ZRadioButtonGroup

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
)

import json
import base64
#}}}

class SelectWorkflow(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.page_name = "Select Workflow"

        self.workflow_type = ZRadioButtonGroup(owner=self, key='workflow_type', default='preshipping')

        self.workflow_type.create_button("packing", "Packing")
        self.workflow_type.create_button("preshipping", "Pre-Shipping")
        self.workflow_type.create_button("shipping", "Shipping")
        self.workflow_type.create_button("transit", "Transit")
        self.workflow_type.create_button("receiving", "Receiving")

        self._construct_page()

    def _construct_page(self):
        #{{{
        screen_layout = QVBoxLayout()

        page_title = QLabel("Select Shipping Workflow")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)


        screen_layout.addSpacing(20)

        screen_layout.addWidget(self.workflow_type.button("packing"))
        screen_layout.addWidget(self.workflow_type.button("preshipping"))
        screen_layout.addWidget(self.workflow_type.button("shipping"))
        screen_layout.addWidget(self.workflow_type.button("transit"))
        screen_layout.addWidget(self.workflow_type.button("receiving"))
        
        screen_layout.addStretch()

        #self.nav_bar = self.parent().NavBar(self.parent())

        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
        #}}}

    def save(self):
        super().save()

    def update(self):
        super().update()
        if self.page_state.get('workflow_type', None) is not None:
            self.nav_bar.continue_button.setEnabled(True)
        else:
            self.nav_bar.continue_button.setEnabled(False)


    def restore(self):
        super().restore()

    #}}}

