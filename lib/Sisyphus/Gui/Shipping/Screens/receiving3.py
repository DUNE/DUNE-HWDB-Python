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


import csv
import json
import smtplib
import os

###############################################################################

class Receiving3(zw.PageWidget):
    
    page_name = "Receiving Workflow (3)"
    page_short_name = "Receiving (3)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.email_contents = zw.ZTextEdit(page=self, key='email_contents')
        
        self.confirm_email_contents = zw.ZCheckBox('I have sent the email',
                        page=self, key='confirm_email_contents')
        self.instructions = qtw.QLabel('Paste the following into an email message and '
                    'send it to the FD Logistics team:')
        self.instructions.setWordWrap(True)

        self.csv_filename = None
        self.csv_full_filename = None

        self._setup_UI()

    def _setup_UI(self):
        #{{{

        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)

        ################
        
        main_layout.addSpacing(10)

        main_layout.addWidget(self.instructions)

        main_layout.addWidget(self.email_contents)
        self.email_contents.setMinimumSize(600, 400)

        ################

        main_layout.addSpacing(15)

        main_layout.addWidget(
            qtw.QLabel("Please affirm before continuing:")
        )
        main_layout.addWidget(
            #QCheckBox("Yes, this looks correct")
            self.confirm_email_contents
        )

        ################

        main_layout.addSpacing(15)

        #main_layout.addWidget(
        #    QLabel("Clicking 'continue' will send this email to the FD Logistics Team")
        #)

        ################
        main_layout.addStretch()

        main_layout.addWidget(self.nav_bar)

        self.setLayout(main_layout)
        #}}}

    def on_navigate_next(self):
        # if I can ever get it to send email, put it here
        return super().on_navigate_next()

    def restore(self):
        super().restore()
        self.generate_email()

    def generate_email(self):
        #{{{
        workflow_state = self.workflow_state

        instructions = ("Please send an email to your POC to let them know the "
                    "shipment has arrived.")
        self.instructions.setText(instructions) 

        email_to = (f"{workflow_state['PreShipping3']['approver_name']} "
                    f"&lt;{workflow_state['PreShipping3']['approver_email']}&gt;")

        email_from = (f"{self.application.user_full_name} "
                    f"&lt;{self.application.user_email}&gt;")
        
        email_subject = "Final Reciving checklist for shipment {self.pid}"
        
        email_msg = (
            f"""<table>"""
            f"""<tr><td width="100">From:</td><td>{email_from}</td></tr>"""
            f"""<tr><td>To:</td><td>{email_to}</td></tr>"""
            f"""<tr><td>Subject:</td><td>{email_subject}</td></tr>"""
            f"""<tr><td colspan="2">&nbsp;</td></tr>"""
            f"""<tr><td colspan="2">"""


            f"Dear {workflow_state['PreShipping3']['approver_name']},<br/>\n<br/>\n"
            f"Your shipment, {self.part_id}, has arrived at "
            f"{workflow_state['Receiving2']['location']} [TODO: lookup inst] at "
            f"{workflow_state['Receiving2']['arrived']} [TODO: format time].<br/>\n<br/>\n"

            f"Sincerely,<br/>\n<br/>\n"
            f"{self.application.user_full_name}<br/>\n"
            f"{self.application.user_email}<br/>\n"
            
            f"""</td>"""            
            f"""</table>"""
        )
        
        #self.email_contents.setText(email_msg)
        self.email_contents.setHtml(email_msg)
        #}}}


    def refresh(self):
        super().refresh()

        if self.confirm_email_contents.isChecked():
            self.nav_bar.continue_button.setEnabled(True)
        else:
            self.nav_bar.continue_button.setEnabled(False)

    #}}}
        
