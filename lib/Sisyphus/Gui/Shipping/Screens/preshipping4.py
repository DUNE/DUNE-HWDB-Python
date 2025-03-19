#!/usr/bin/env python

from Sisyphus.Configuration import config, USER_SETTINGS_DIR
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut

from Sisyphus.Utils.Terminal.Style import Style

from Sisyphus.Gui.Shipping.Widgets import PageWidget
from Sisyphus.Gui.Shipping.Widgets import ZLineEdit, ZTextEdit, ZCheckBox

from Sisyphus.Gui.Shipping.ShippingLabel import ShippingLabel

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
    QGroupBox,
    QButtonGroup,
)
import csv
import json
import smtplib
import os

class PreShipping4(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.email_contents = ZTextEdit(parent=self, key='email_contents')
        
        self.confirm_email_contents = ZCheckBox('I have sent the email',
                        parent=self, key='confirm_email_contents')
        self.instructions = QLabel('Paste the following into an email message and '
                    'send it to the FD Logistics team:')
        self.instructions.setWordWrap(True)

        self.csv_filename = None
        self.csv_full_filename = None

        self._construct_page()

    def _construct_page(self):
        #{{{

        screen_layout = QVBoxLayout()
        ########################################

        page_title = QLabel("Pre-Shipping Workflow (4)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        ################
        screen_layout.addSpacing(10)

        screen_layout.addWidget(self.instructions)

        screen_layout.addWidget(self.email_contents)
        self.email_contents.setMinimumSize(600, 400)

        ################

        screen_layout.addSpacing(15)

        screen_layout.addWidget(
            QLabel("Please affirm before continuing:")
        )
        screen_layout.addWidget(
            #QCheckBox("Yes, this looks correct")
            self.confirm_email_contents
        )

        ################

        screen_layout.addSpacing(15)

        #screen_layout.addWidget(
        #    QLabel("Clicking 'continue' will send this email to the FD Logistics Team")
        #)

        ################
        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
        #}}}

    def on_navigate_next(self):
        '''
        sender = 'alexcwagner@gmail.com'
        receivers = 'alexcwagner@gmail.com'
        message = 'This is a test email message.'

        try:
            smtp_obj = smtplib.SMTP('localhost')
            smtp_obj.sendmail(sender, receivers, message)
            print("Successfully sent email")
        except smtplib.SMTPException:
            Style.error.print("SMTPException: unable to send email")
        except Exception as exc:
            Style.error.print(f"Error sending email: {exc}")
        '''
        return

    def restore(self):
        super().restore()
        self.generate_csv()
        self.generate_email()

    def generate_email(self):
        tab_state = self.tab_state

        if self.csv_filename is None:
            self.generate_csv()

        instructions = (
                    'A CSV file has been generated at '
                    f'<b>{self.csv_filename}</b>.<br/><br/>'
                    'Paste the following into an email message, attach '
                    f'the CSV file and '
                    'send it to the FD Logistics team:')
        self.instructions.setText(instructions) 



        poc_email = (f"{tab_state['PreShipping2']['approver_name']} "
                    f"&lt;{tab_state['PreShipping2']['approver_email']}&gt;")

        email_from = (f"{tab_state['SelectPID']['user_name']} "
                    f"&lt;{tab_state['SelectPID']['user_email']}&gt;")
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
            f"{tab_state['SelectPID']['user_name']}<br/>\n"
            f"{tab_state['SelectPID']['user_email']}<br/>\n"
            f"Attachment: {self.csv_filename}\n"

            f"""</td"""            
            f"""</table>"""
        )
        
        #self.email_contents.setText(email_msg)
        self.email_contents.setHtml(email_msg)


    def generate_csv(self):
        #{{{
        print("Creating CSV...")
        
        self.csv_filename = f"{self.tab_state['part_id']}-preshipping.csv"
        self.csv_full_filename = os.path.realpath(self.csv_filename)

        with open(self.csv_filename, 'w') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')

            csvwriter.writerow([
                "Dimension",
                self.tab_state['PreShipping3a']['dimension']
            ])
            csvwriter.writerow([
                "Weight",
                self.tab_state['PreShipping3a']['weight']
            ])
            csvwriter.writerow([
                "Freight Forwarder name",
                self.tab_state['PreShipping3b']['freight_forwarder']
            ])
            csvwriter.writerow([
                "Mode of Transportation",
                self.tab_state['PreShipping3b']['mode_of_transportation']
            ])
            csvwriter.writerow([
                "Expected Arrival Date (CST)",
                self.tab_state['PreShipping3b']['expected_arrival_time']
            ])
            csvwriter.writerow([
                "Shipment's origin",
                self.tab_state['PreShipping3a']['shipment_origin']
            ])
            csvwriter.writerow([
                "HTS code",
                self.tab_state['PreShipping3a']['hts_code']
            ])
            csvwriter.writerow([])
            csvwriter.writerow([
                "QA/QC related information for this shipment can be found here",
                self.tab_state['PreShipping2']['test_info']
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
                self.tab_state['part_id']
            ])
            csvwriter.writerow([])
            csvwriter.writerow([
                "Sub-component PID",
                "Component Type Name",
                "Func. Pos. Name"
            ])
        #}}}
    #}}}
        
