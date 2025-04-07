#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

#{{{
from Sisyphus.Gui.Shipping.Widgets import PageWidget, NavBar
from Sisyphus.Gui.Shipping.Widgets import ZTextEdit, ZCheckBox

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
#}}}
class Shipping3(PageWidget):
    page_name = "Shipping Workflow (3)"
    page_short_name = "Shipping (3)"

    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.email_contents = ZTextEdit(owner=self, key='email_contents')

        self.confirm_email_contents = ZCheckBox('I have sent the email',
                        owner=self, key='confirm_email_contents')
        self.instructions = QLabel('Paste the following into an email message and '
                    'send it to the FD Logistics team:')
        self.instructions.setWordWrap(True)

        self._setup_UI()

    def _setup_UI(self):
        #{{{
        screen_layout = QVBoxLayout()

        #############################
        page_title = QLabel("Shipping Workflow (3)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        #############################
        
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


        #############################

        screen_layout.addStretch()

        screen_layout.addWidget(self.nav_bar)
        self.setLayout(screen_layout)
        #}}}

    def restore(self):
        super().restore()
        self.generate_email()

    def generate_email(self):
        #{{{
        tab_state = self.tab_state

        instructions = (
                    'Paste the following into an email message, attach '
                    f'the BoL and the Proforma Invoice (if applicable) and '
                    'send it to the FD Logistics team:')
        self.instructions.setText(instructions)



        poc_email = (f"{tab_state['PreShipping2']['approver_name']} "
                    f"&lt;{tab_state['PreShipping2']['approver_email']}&gt;")

        email_from = (f"{tab_state['SelectPID']['user_name']} "
                    f"&lt;{tab_state['SelectPID']['user_email']}&gt;")
        email_to = f"FD Logistics Team &lt;sdshipments@fnal.gov&gt;"
        email_subject = (f"Request for the final approval for shipment PID = "
                            f"{self.tab_state['part_info']['part_id']}")

        email_msg = (
            f"""<table>"""
            f"""<tr><td width="100">From:</td><td>{email_from}</td></tr>"""
            f"""<tr><td>To:</td><td>{email_to}</td></tr>"""
            f"""<tr><td>Subject:</td><td>{email_subject}</td></tr>"""
            f"""<tr><td colspan="2">&nbsp;</td></tr>"""
            f"""<tr><td colspan="2">"""


            f"Dear FD Logistics team,<br/>\n<br/>\n"
            f"I would like to request a new shipment. "
            #f"Please find the attached csv file, {self.csv_filename}, that contains the "
            #f"required information for this shipment.<br/>\n"
            f"Should there be any issue with this "
            f"shipment, email to:\n"
            f"<ul><li>{poc_email}</li></ul>\n"
            f"Sincerely,<br/>\n<br/>\n"
            f"{tab_state['SelectPID']['user_name']}<br/>\n"
            f"{tab_state['SelectPID']['user_email']}<br/>\n"
            #f"Attachment: {self.csv_filename}\n"

            f"""</td>"""
            f"""</table>"""
        )

        #self.email_contents.setText(email_msg)
        self.email_contents.setHtml(email_msg)
        #}}}

    def update(self):
        super().update()

        if self.confirm_email_contents.isChecked():
            self.nav_bar.continue_button.setEnabled(True)
        else:
            self.nav_bar.continue_button.setEnabled(False)



    #}}}


