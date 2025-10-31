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


class PreShipping2(PageWidget):
    page_name = "Pre-Shipping Workflow (2)"
    page_short_name = "Pre-Shipping (2)"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self.page_name = "Pre-Shipping (2)"

        self.qa_rep_name = zw.ZLineEdit(page=self, key='qa_rep_name')
        self.qa_rep_email = zw.ZLineEdit(page=self, key='qa_rep_email')
        self.test_info = zw.ZTextEdit(page=self, key='test_info')

        self._setup_UI()

    def _setup_UI(self):
        #{{{
        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)
        ########################################

        #main_layout.addWidget(
        #    qtw.QLabel("Provide the name and email of the QA Rep")
        #)

        self.QARepmess = qtw.QLabel("Provide the name and email address of your Consortium QA Representative "
                        "who has approved this shipment by setting both the Consortium Certified Status flag and the All QA/QC Test and Documentation flag in the HWDB.")
        self.QARepmess.setWordWrap(True)
        #QARepmess.setStyleSheet("""
        #        font-size: 14pt;
        #    """)
        main_layout.addWidget(self.QARepmess)

        self.QARepmessMultiple = qtw.QLabel("(For multiple email addresses, each address should be separated by a comma)")
        main_layout.addWidget(self.QARepmessMultiple)

        

        ################

        contact_info_layout = qtw.QVBoxLayout()

        name_layout = qtw.QVBoxLayout()
        self.name_label = qtw.QLabel("Name")
        name_layout.addWidget(self.name_label)
        #name_layout.addWidget(QLineEdit("Joe Schmoe"))
        name_layout.addWidget(self.qa_rep_name)
        name_layout_widget = qtw.QWidget(self)
        name_layout_widget.setLayout(name_layout)
        
        email_layout = qtw.QVBoxLayout()
        self.email_label = qtw.QLabel("Email")
        email_layout.addWidget(self.email_label)
        email_layout.addWidget(self.qa_rep_email)
        email_layout_widget = qtw.QWidget(self)
        email_layout_widget.setLayout(email_layout)

        contact_info_layout.addWidget(name_layout_widget)
        contact_info_layout.addWidget(email_layout_widget)


        contact_info_layout_widget = qtw.QWidget(self)
        contact_info_layout_widget.setLayout(contact_info_layout)

        main_layout.addWidget(contact_info_layout_widget)

        ################

        #test_info_label = qtw.QLabel("Provide information on where the corresponding QA/QC test results "
        #        "can be found (e.g., link(s) to test results in the HWDB) and a EDMS or "
        #        "doc-DB # of the corresponding documentation.")
        #test_info_label.setWordWrap(True)
        #main_layout.addWidget(test_info_label)

        #test_info_layout = qtw.QVBoxLayout()
        
        #test_info_layout.addWidget(self.test_info)
        #test_info_widget = qtw.QWidget()
        #test_info_widget.setLayout(test_info_layout)

        #main_layout.addWidget(test_info_widget)

        ################
        #select_pid_state = self.workflow_state.get("SelectPID", {})
        #is_surf = select_pid_state.get("confirm_surf", False)
        #if not is_surf:
        #    self.qa_rep_name.setReadOnly(True)
        #    self.qa_rep_email.setReadOnly(True)
        #else:
        #    self.qa_rep_name.setEnabled(True)
        #    self.qa_rep_name.setReadOnly(False)
        #    self.qa_rep_name.setStyleSheet("")
        #    self.qa_rep_email.setEnabled(True)
        #    self.qa_rep_email.setReadOnly(False)
        #    self.qa_rep_name.setStyleSheet("")
        #    self.qa_rep_email.setStyleSheet("")
        ################
        main_layout.addStretch()

        main_layout.addWidget(self.nav_bar)

        self.setLayout(main_layout)
        #}}}

    def refresh(self):
        super().refresh()

        # show this only if shipping to SURF
        select_pid_state = self.workflow_state.get("SelectPID", {})
        is_surf = select_pid_state.get("confirm_surf", False)
        # --- dynamically show/hide things ---
        if not is_surf:
            self.QARepmess.hide()
            self.QARepmessMultiple.hide()
            self.name_label.hide()
            self.qa_rep_name.hide()
            self.email_label.hide()
            self.qa_rep_email.hide()
        else:
            self.QARepmess.show()
            self.QARepmessMultiple.show()
            self.name_label.show()
            self.qa_rep_name.show()
            self.email_label.show()
            self.qa_rep_email.show()


        if is_surf:
            if ( len(self.qa_rep_name.text()) > 0 
                    and len(self.qa_rep_email.text()) > 0 ):
                #and len(self.test_info.toPlainText()) > 0 ):
                self.nav_bar.continue_button.setEnabled(True)
            else:
                self.nav_bar.continue_button.setEnabled(False)
        else:
            self.nav_bar.continue_button.setEnabled(True)
