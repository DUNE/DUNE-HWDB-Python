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
from Sisyphus.Gui.Shipping.Widgets.PageWidget import PageWidget

from PyQt5 import QtWidgets as qtw

import json


class PreShipping3(PageWidget):
    page_name = "Pre-Shipping Workflow : Step 3"
    page_short_name = "Pre-Shipping (3)"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.approver_name = zw.ZLineEdit(page=self, key='approver_name')
        self.approver_email = zw.ZLineEdit(page=self, key='approver_email')

        self._setup_UI()

    def _setup_UI(self):
        #{{{
        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)
        ########################################

        #main_layout.addWidget(
        #    qtw.QLabel("Provide the person's name and email address who has approved this shipment")
        #)

        POCmess = qtw.QLabel("Provide the name and email address the point of contact (POC) person for this shipment.")
        POCmess.setStyleSheet("""
                font-size: 15pt;
            """)
        POCmess.setWordWrap(True)
        main_layout.addWidget(POCmess)
        POCmess2 = qtw.QLabel("This POC will be also contacted in case of shipment failure.")
        POCmess2.setStyleSheet("""
                font-size: 15pt;
            """)
        POCmess2.setWordWrap(True)
        main_layout.addWidget(POCmess2)

        mulemailmess = qtw.QLabel("(For multiple email addresses, each address should be separated by a comma)")
        mulemailmess.setWordWrap(True)
        mulemailmess.setStyleSheet("""
                font-size: 15pt;
            """)
        main_layout.addWidget(mulemailmess)

        ################

        contact_info_layout = qtw.QVBoxLayout()

        name_layout = qtw.QVBoxLayout()
        myname = qtw.QLabel("Name")
        myname.setStyleSheet("""
                font-size: 15pt;
            """)
        name_layout.addWidget(myname)
        name_layout.addWidget(self.approver_name)
        name_layout_widget = qtw.QWidget(self)
        name_layout_widget.setLayout(name_layout)
        
        email_layout = qtw.QVBoxLayout()
        myemail = qtw.QLabel("Email")
        myemail.setStyleSheet("""
                font-size: 15pt;
            """)
        email_layout.addWidget(myemail)
        email_layout.addWidget(self.approver_email)
        email_layout_widget = qtw.QWidget(self)
        email_layout_widget.setLayout(email_layout)

        contact_info_layout.addWidget(name_layout_widget)
        contact_info_layout.addWidget(email_layout_widget)


        contact_info_layout_widget = qtw.QWidget(self)
        contact_info_layout_widget.setLayout(contact_info_layout)

        main_layout.addWidget(contact_info_layout_widget)

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
