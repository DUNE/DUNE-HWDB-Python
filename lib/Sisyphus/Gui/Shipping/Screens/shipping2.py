#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

#{{{
from Sisyphus.Gui.Shipping.Widgets import PageWidget, NavBar
from Sisyphus.Gui.Shipping.Widgets import ZLineEdit, ZFileSelectWidget

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
    QFileDialog,
)
#}}}

class Shipping2(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #self.bol_text = ZLineEdit(owner=self, key="bol_filename")
        #self.select_bol_button = QPushButton("Select BoL file")
        #self.select_bol_button.clicked.connect(self.select_bol_dialog)

        self.bol_file = ZFileSelectWidget(owner=self, key='bol_filename')

        self.proforma_container = QWidget()
        self.proforma_file = ZFileSelectWidget(owner=self, key='proforma_filename')

        self._construct_page()
        self.update()

    def _construct_page(self):
        #{{{
        screen_layout = QVBoxLayout()

        #############################
        page_title = QLabel("Shipping Workflow (2)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        #############################


        screen_layout.addWidget(
                QLabel("Select Bill of Lading image file:"))
        screen_layout.addWidget(self.bol_file)
       
        screen_layout.addSpacing(20)
 

        proforma_layout = QVBoxLayout()
        proforma_layout.setContentsMargins(0, 0, 0, 0)
        self.proforma_container.setLayout(proforma_layout)
        screen_layout.addWidget(self.proforma_container)

        #screen_layout.addWidget(
        #        QLabel("Select Proforma image file:"))
        #screen_layout.addWidget(self.proforma_file)
        proforma_layout.addWidget(
                QLabel("Select Proforma image file:"))
        proforma_layout.addWidget(self.proforma_file)


        #############################
        screen_layout.addStretch()
        screen_layout.addWidget(self.nav_bar)
        self.setLayout(screen_layout)
        #}}}

    def select_bol_dialog(self):
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Select Bill of Lading Image File")

        if file_dialog.exec():
            self.bol_text.setText(file_dialog.selectedFiles()[0])

    def update(self):
        super().update()

        shipping_service_type = self.tab_state.get('PreShipping3a', {}) \
                    .get('shipping_service_type', 'Domestic')
        if shipping_service_type != "International":
            self.proforma_container.setEnabled(False)
            self.page_state['proforma_filename'] = ''
            self.proforma_file.restore()
        else:
            self.proforma_container.setEnabled(True)

        if ( self.page_state.get('bol_filename', '') == ''
                or ( shipping_service_type == 'International' 
                        and self.page_state.get('proforma_filename', '') == '')):
            self.nav_bar.continue_button.setEnabled(False)
        else:
            self.nav_bar.continue_button.setEnabled(True)

    #}}}
