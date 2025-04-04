#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

#{{{
from Sisyphus.Gui.Shipping.Widgets import PageWidget, NavBar
from Sisyphus.Gui.Shipping.Widgets import (                                                                                 ZLineEdit, ZTextEdit, ZCheckBox, ZDateTimeEdit, ZRadioButtonGroup,
            ZFileSelectWidget)

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

#}}}
class Shipping4(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_name = "Shipping (4)"

        self.received_approval = ZCheckBox("Yes, I have received an approval",
                    owner=self, key='received_approval')

        self.approved_by = ZLineEdit(owner=self, key='approved_by')

        self.approved_time = ZDateTimeEdit(owner=self, key='approved_time')

        self.approval_image = ZFileSelectWidget(owner=self, key='approved_image')

        msg = "The DUNE Shipping Sheet has been securely attached to the shipment"
        self.confirm_attached_sheet = ZCheckBox(owner=self, text=msg, key="confirm_attached_sheet")

        msg = "The cargo has been adequately insured for transit"
        self.confirm_insured = ZCheckBox(owner=self, text=msg, key="confirm_insured")

        self._construct_page()

    def _construct_page(self):
        #{{{
        screen_layout = QVBoxLayout()
        ########################################

        page_title = QLabel("Shipping Workflow (4)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)

        ################

        label1 = QLabel(
                "An email has been sent to the FD Logistics Team. "
                "Do not continue until you have received an approval from them."
        )
        label1.setWordWrap(True)
        screen_layout.addWidget(label1)
        screen_layout.addSpacing(15)


        screen_layout.addWidget(
            QLabel("Have you received an approval from the FD Logistics team?")
        )

        screen_layout.addWidget(
            self.received_approval
        )

        screen_layout.addWidget(QLabel("Approved by whom?"))
        screen_layout.addWidget(self.approved_by)

        screen_layout.addWidget(QLabel("When approved (date/time in Central Time)?"))
        screen_layout.addWidget(self.approved_time)

        screen_layout.addSpacing(15)
        screen_layout.addWidget(
            QLabel("Take a photo or screenshot of the approved message and upload it")
        )

        screen_layout.addWidget(self.approval_image)

        screen_layout.addSpacing(15)
        
        ################

        screen_layout.addWidget(QLabel("Please affirm the following:"))

        affirm_layout = QHBoxLayout()
        affirm_layout.addSpacing(10)

        indented_layout = QVBoxLayout()
        indented_layout.addWidget(self.confirm_attached_sheet)
        indented_layout.addWidget(self.confirm_insured)
        indented_widget = QWidget()
        indented_widget.setLayout(indented_layout)
        affirm_layout.addWidget(indented_widget)
        affirm_widget = QWidget()
        affirm_widget.setLayout(affirm_layout)
        screen_layout.addWidget(affirm_widget)
        ################

        screen_layout.addStretch()

        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
        #}}}

    def update(self):
        super().update()

        if not self.received_approval.isChecked():
            self.nav_bar.continue_button.setEnabled(False)
            return
        if not self.confirm_attached_sheet.isChecked():
            self.nav_bar.continue_button.setEnabled(False)
            return
        if not self.confirm_insured.isChecked():
            self.nav_bar.continue_button.setEnabled(False)
            return

        if len(self.approved_by.text()) == 0:
            self.nav_bar.continue_button.setEnabled(False)
            return

        if len(self.page_state['approved_image']) == 0:
            self.nav_bar.continue_button.setEnabled(False)

        self.nav_bar.continue_button.setEnabled(True)

    #}}}
