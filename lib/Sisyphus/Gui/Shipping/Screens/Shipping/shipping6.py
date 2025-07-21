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
from Sisyphus.Gui.Shipping.Widgets.PageWidget import PageWidget

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

from datetime import datetime
import csv
import json
import smtplib
import os

###############################################################################

class Shipping6(PageWidget):
    page_name = "Shipping Workflow (6)"
    page_short_name = "Shipping (6)"

    def __init__(self, *args, **kwargs):
        #{{{
        super().__init__(*args, **kwargs)

        self.instructions = qtw.QLabel('')
        self.instructions.setWordWrap(True)

        self._setup_UI()
        #}}}

    def _setup_UI(self):
        #{{{
        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)

        #############################

        main_layout.addWidget(self.instructions)
        main_layout.addWidget(
            qtw.QLabel(
                    #f"A CSV file {self.csv_filename} has been saved in your working directory.\n"
                    "(Optional)\n"
                    "You may wish to email it and other documents to your collaborators."))

        main_layout.addStretch()

        main_layout.addWidget(self.nav_bar)
        self.setLayout(main_layout)
        #}}}

    def refresh(self):
        super().refresh()

    def restore(self):
        super().restore()
        self.generate_csv()
        # Display the message
        instructions = (
                    'A CSV file has been generated at '
                    f'<b>{self.csv_full_filename}</b>.<br/><br/>')
        self.instructions.setText(instructions)
        

    def generate_csv(self):
        #{{{
        #print("Creating CSV...")

        mycurrenttime = datetime.now().strftime("%Y-%m-%d-%H-%M")
        self.csv_filename = f"{self.workflow_state['part_info']['part_id']}-shipping-{mycurrenttime}.csv"
        #self.csv_filename = f"{self.workflow_state['part_info']['part_id']}-preshipping.csv"


        self.csv_full_filename = os.path.join(
                self.workflow.working_directory, self.csv_filename)

        with open(self.csv_full_filename, 'w') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')

            csvwriter.writerow([
                "POC name",
                self.workflow_state['PreShipping3']['approver_name']
            ])
            csvwriter.writerow([
                "POC Email",
                self.workflow_state['PreShipping3']['approver_email']
            ])
            csvwriter.writerow([
                "System Name (ID)",
                f"{self.workflow_state['part_info']['system_name']} ({self.workflow_state['part_info']['system_id']})"
            ])
            csvwriter.writerow([
                "Subsystem Name (ID)",
                f"{self.workflow_state['part_info']['subsystem_name']} ({self.workflow_state['part_info']['subsystem_id']})"
            ])
            csvwriter.writerow([
                "Component Type Name (ID)",
                f"{self.workflow_state['part_info']['part_type_name']} ({self.workflow_state['part_info']['part_type_id']})"
            ])
            csvwriter.writerow([
                "DUNE PID",
                self.workflow_state['part_info']['part_id']
            ])
            csvwriter.writerow([
                "Image ID for BoL",
                self.workflow_state['Shipping2']['bol_info']['image_id']
            ])
            csvwriter.writerow([
                "Image ID for the final approval message",
                self.workflow_state['Shipping4']['approval_info']['image_id']
            ])
            csvwriter.writerow([
                "FD Logistics team final approval (name)",
                self.workflow_state['Shipping4']['approved_by']
            ])
            csvwriter.writerow([
                "FD Logistics team final approval (date in CT)",
                self.workflow_state['Shipping4']['approved_time']
            ])
            csvwriter.writerow([
                "DUNE Shipping Sheet has been attached",
                self.workflow_state['Shipping4']['confirm_attached_sheet']
            ])
            csvwriter.writerow([
                "This shipment has been adequately insured for transit",
                self.workflow_state['Shipping4']['confirm_insured']
            ])
            #csvwriter.writerow([
            #    "Sub-component PID",
            #    "Component Type Name",
            #    "Func. Pos. Name"
            #])
            csvwriter.writerow([
                "SubPIDs:"
            ])
            for sc in self.workflow_state['part_info'].get('subcomponents', {}).values():
                #csvwriter.writerow([
                #    sc['Sub-component PID'],
                #    sc['Component Type Name'],
                #    sc['Functional Position Name'],
                #])
                csvwriter.writerow([
                    f"{sc['Component Type Name']} ({sc['Functional Position Name']}),{sc['Sub-component PID']}"
                ])
        #}}}