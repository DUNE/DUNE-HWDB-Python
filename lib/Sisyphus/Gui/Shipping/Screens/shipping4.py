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


class Shipping4(zw.PageWidget):
    page_name = "Shipping Workflow (4)"
    page_short_name = "Shipping (4)"

    def __init__(self, *args, **kwargs):
        #{{{
        super().__init__(*args, **kwargs)

        self.received_approval = zw.ZCheckBox("Yes, I have received an approval",
                    owner=self, key='received_approval')
        self.approved_by = zw.ZLineEdit(owner=self, key='approved_by')
        self.approved_time = zw.ZDateTimeEdit(owner=self, key='approved_time')
        self.approval_image = zw.ZFileSelectWidget(owner=self, key='approved_image')

        msg = "The DUNE Shipping Sheet has been securely attached to the shipment"
        self.confirm_attached_sheet = zw.ZCheckBox(owner=self, text=msg, key="confirm_attached_sheet")

        msg = "The cargo has been adequately insured for transit"
        self.confirm_insured = zw.ZCheckBox(owner=self, text=msg, key="confirm_insured")

        self._setup_UI()
        #}}}

    def _setup_UI(self):
        #{{{
        screen_layout = qtw.QVBoxLayout()
        ########################################

        page_title = qtw.QLabel("Shipping Workflow (4)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(qtc.Qt.AlignCenter)
        screen_layout.addWidget(page_title)

        ################

        label1 = qtw.QLabel(
                "An email has been sent to the FD Logistics Team. "
                "Do not continue until you have received an approval from them."
        )
        label1.setWordWrap(True)
        screen_layout.addWidget(label1)
        screen_layout.addSpacing(15)


        screen_layout.addWidget(
            qtw.QLabel("Have you received an approval from the FD Logistics team?")
        )

        screen_layout.addWidget(
            self.received_approval
        )

        screen_layout.addWidget(qtw.QLabel("Approved by whom?"))
        screen_layout.addWidget(self.approved_by)

        screen_layout.addWidget(qtw.QLabel("When approved (date/time in Central Time)?"))
        screen_layout.addWidget(self.approved_time)

        screen_layout.addSpacing(15)
        screen_layout.addWidget(
            qtw.QLabel("Take a photo or screenshot of the approved message and upload it")
        )

        screen_layout.addWidget(self.approval_image)

        screen_layout.addSpacing(15)
        
        ################

        screen_layout.addWidget(qtw.QLabel("Please affirm the following:"))

        affirm_layout = qtw.QHBoxLayout()
        affirm_layout.addSpacing(10)

        indented_layout = qtw.QVBoxLayout()
        indented_layout.addWidget(self.confirm_attached_sheet)
        indented_layout.addWidget(self.confirm_insured)
        indented_widget = qtw.QWidget()
        indented_widget.setLayout(indented_layout)
        affirm_layout.addWidget(indented_widget)
        affirm_widget = qtw.QWidget()
        affirm_widget.setLayout(affirm_layout)
        screen_layout.addWidget(affirm_widget)
        ################

        screen_layout.addStretch()
        screen_layout.addWidget(self.nav_bar)
        self.setLayout(screen_layout)
        #}}}

    def update(self):
        #{{{
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


