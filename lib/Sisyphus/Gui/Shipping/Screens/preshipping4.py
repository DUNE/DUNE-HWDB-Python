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
from Sisyphus.Gui.Shipping.ShippingLabel import ShippingLabel

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw


import csv
import json
import smtplib
import os

###############################################################################

class PreShipping4(zw.PageWidget):
    
    page_name = "Pre-Shipping Workflow (4)"
    page_short_name = "Pre-Shipping (4)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.email_contents = zw.ZTextEdit(owner=self, key='email_contents')
        
        self.confirm_email_contents = zw.ZCheckBox('I have sent the email',
                        owner=self, key='confirm_email_contents')
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
        self.generate_csv()
        self.generate_email()

    def generate_email(self):
        #{{{
        workflow_state = self.workflow_state

        if self.csv_filename is None:
            self.generate_csv()

        instructions = (
                    'A CSV file has been generated at '
                    f'<b>{self.csv_filename}</b>.<br/><br/>'
                    'Paste the following into an email message, attach '
                    f'the CSV file and '
                    'send it to the FD Logistics team:')
        self.instructions.setText(instructions) 



        poc_email = (f"{workflow_state['PreShipping2b']['approver_name']} "
                    f"&lt;{workflow_state['PreShipping2b']['approver_email']}&gt;")

        email_from = (f"{self.application.user_full_name} "
                    f"&lt;{self.application.user_email}&gt;")
        email_to = f"FD Logistics Team &lt;sdshipments@fnal.gov&gt;"
        email_subject = "Request an acknowledgement for a new shipment"
        
        email_msg = (
            f"""<table>"""
            f"""<tr><td width="100">From:</td><td>{email_from}</td></tr>"""
            f"""<tr><td>To:</td><td>{email_to}</td></tr>"""
            f"""<tr><td>Subject:</td><td>{email_subject}</td></tr>"""
            f"""<tr><td colspan="2">&nbsp;</td></tr>"""
            f"""<tr><td colspan="2">"""


            f"Dear FD Logistics team,<br/>\n<br/>\n"
            f"I would like to request a new shipment. "
            f"Please find the attached csv file, {self.csv_filename}, that contains the "
            f"required information for this shipment. Should there be any issue with this "
            f"shipment, email to:\n"
            f"<ul><li>{poc_email}</li></ul>\n"
            f"Sincerely,<br/>\n<br/>\n"
            f"{self.application.user_full_name}<br/>\n"
            f"{self.application.user_email}<br/>\n"
            f"Attachment: {self.csv_filename}\n"

            f"""</td>"""            
            f"""</table>"""
        )
        
        #self.email_contents.setText(email_msg)
        self.email_contents.setHtml(email_msg)
        #}}}

    def generate_csv(self):
        #{{{
        print("Creating CSV...")

        self.csv_filename = f"{self.workflow_state['part_info']['part_id']}-preshipping.csv"
        self.csv_full_filename = os.path.join(
                self.workflow.working_directory, self.csv_filename)

        with open(self.csv_full_filename, 'w') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')

            csvwriter.writerow([
                "Dimension",
                self.workflow_state['PreShipping3a']['dimension']
            ])
            csvwriter.writerow([
                "Weight",
                self.workflow_state['PreShipping3a']['weight']
            ])
            csvwriter.writerow([
                "Freight Forwarder name",
                self.workflow_state['PreShipping3b']['freight_forwarder']
            ])
            csvwriter.writerow([
                "Mode of Transportation",
                self.workflow_state['PreShipping3b']['mode_of_transportation']
            ])
            csvwriter.writerow([
                "Expected Arrival Date (CST)",
                self.workflow_state['PreShipping3b']['expected_arrival_time']
            ])
            csvwriter.writerow([
                "Shipment's origin",
                self.workflow_state['PreShipping3a']['shipment_origin']
            ])
            csvwriter.writerow([
                "HTS code",
                self.workflow_state['PreShipping3a']['hts_code']
            ])
            csvwriter.writerow([])
            csvwriter.writerow([
                "QA/QC related information for this shipment can be found here",
                self.workflow_state['PreShipping2a']['test_info']
            ])
            csvwriter.writerow([])
            csvwriter.writerow([
                "System Name (ID)",
                "TBD"
            ])
            csvwriter.writerow([
                "Subsystem Name (ID)",
                "TBD"
            ])
            csvwriter.writerow([
                "Component Type Name (ID)",
                "TBD"
            ])
            csvwriter.writerow([
                "DUNE PID",
                self.workflow_state['part_info']['part_id']
            ])
            csvwriter.writerow([])
            csvwriter.writerow([
                "Sub-component PID",
                "Component Type Name",
                "Func. Pos. Name"
            ])
            for sc in self.workflow_state['part_info'].get('subcomponents', {}).values():
                csvwriter.writerow([
                    sc['Sub-component PID'],
                    sc['Component Type Name'],
                    sc['Functional Position Name'],
                ])
        #}}}

    def refresh(self):
        super().refresh()

        if self.confirm_email_contents.isChecked():
            self.nav_bar.continue_button.setEnabled(True)
        else:
            self.nav_bar.continue_button.setEnabled(False)

    #}}}
        
