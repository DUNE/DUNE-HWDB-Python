#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus.Gui.Shipping import Widgets as zw
from Sisyphus.Gui.Shipping import Model as mdl

from PyQt5 import QtWidgets as qtw

import json


class PreShipping2b(zw.PageWidget):
    page_name = "Pre-Shipping Workflow (2b)"
    page_short_name = "Pre-Shipping (2b)"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.approver_name = zw.ZLineEdit(owner=self, key='approver_name')
        self.approver_email = zw.ZLineEdit(owner=self, key='approver_email')
        #self.test_info = zw.ZTextEdit(owner=self, key='test_info')

        self._setup_UI()

    def _setup_UI(self):
        #{{{
        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)
        ########################################

        main_layout.addWidget(
            qtw.QLabel("Provide the person's name and email address who has approved this shipment")
        )

        main_layout.addWidget(
            qtw.QLabel("(For multiple email addresses, each address should be separated by a comma)")
        )

        ################

        contact_info_layout = qtw.QVBoxLayout()

        name_layout = qtw.QVBoxLayout()
        name_layout.addWidget(qtw.QLabel("Name"))
        #name_layout.addWidget(QLineEdit("Joe Schmoe"))
        name_layout.addWidget(self.approver_name)
        name_layout_widget = qtw.QWidget(self)
        name_layout_widget.setLayout(name_layout)
        
        email_layout = qtw.QVBoxLayout()
        email_layout.addWidget(qtw.QLabel("Email"))
        email_layout.addWidget(self.approver_email)
        email_layout_widget = qtw.QWidget(self)
        email_layout_widget.setLayout(email_layout)

        contact_info_layout.addWidget(name_layout_widget)
        contact_info_layout.addWidget(email_layout_widget)


        contact_info_layout_widget = qtw.QWidget(self)
        contact_info_layout_widget.setLayout(contact_info_layout)

        main_layout.addWidget(contact_info_layout_widget)

        ################

        '''
        test_info_label = qtw.QLabel("Provide information on where the corresponding QA/QC test results "
                "can be found (e.g., link(s) to test results in the HWDB) and a EDMS or "
                "doc-DB # of the corresponding documentation.")
        test_info_label.setWordWrap(True)
        main_layout.addWidget(test_info_label)

        test_info_layout = qtw.QVBoxLayout()
        #test_info_layout.addWidget(QTextEdit(self))
        test_info_layout.addWidget(self.test_info)
        test_info_widget = qtw.QWidget()
        test_info_widget.setLayout(test_info_layout)

        main_layout.addWidget(test_info_widget)
        '''

        ################
        main_layout.addStretch()

        main_layout.addWidget(self.nav_bar)

        self.setLayout(main_layout)
        #}}}

    def refresh(self):
        super().refresh()

        if ( len(self.approver_name.text()) > 0 
                and len(self.approver_email.text()) > 0):
                #and len(self.test_info.toPlainText()) > 0 ):
            self.nav_bar.continue_button.setEnabled(True)
        else:
            self.nav_bar.continue_button.setEnabled(False)
