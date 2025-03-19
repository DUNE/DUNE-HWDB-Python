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

import json


class PreShipping2(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.approver_name = ZLineEdit(parent=self, key='approver_name')
        self.approver_email = ZLineEdit(parent=self, key='approver_email')
        self.test_info = ZTextEdit(parent=self, key='test_info')

        self._construct_page()

    def _construct_page(self):
        #{{{
        screen_layout = QVBoxLayout()
        ########################################

        page_title = QLabel("Pre-Shipping Workflow (2)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        ################


        screen_layout.addWidget(
            QLabel("Provide the person's name and email address who has approved this shipment")
        )

        screen_layout.addWidget(
            QLabel("(For multiple email addresses, each address should be separated by a comma)")
        )

        ################

        contact_info_layout = QVBoxLayout(self)

        name_layout = QVBoxLayout()
        name_layout.addWidget(QLabel("Name"))
        #name_layout.addWidget(QLineEdit("Joe Schmoe"))
        name_layout.addWidget(self.approver_name)
        name_layout_widget = QWidget(self)
        name_layout_widget.setLayout(name_layout)

        email_layout = QVBoxLayout()
        email_layout.addWidget(QLabel("Email"))
        email_layout.addWidget(self.approver_email)
        email_layout_widget = QWidget(self)
        email_layout_widget.setLayout(email_layout)

        contact_info_layout.addWidget(name_layout_widget)
        contact_info_layout.addWidget(email_layout_widget)


        contact_info_layout_widget = QWidget(self)
        contact_info_layout_widget.setLayout(contact_info_layout)

        screen_layout.addWidget(contact_info_layout_widget)

        ################

        test_info_label = QLabel("Provide information on where the corresponding QA/QC test results "
                "can be found (e.g., link(s) to test results in the HWDB) and a EDMS or "
                "doc-DB # of the corresponding documentation.")
        test_info_label.setWordWrap(True)
        screen_layout.addWidget(test_info_label)

        test_info_layout = QVBoxLayout()
        #test_info_layout.addWidget(QTextEdit(self))
        test_info_layout.addWidget(self.test_info)
        test_info_widget = QWidget()
        test_info_widget.setLayout(test_info_layout)

        screen_layout.addWidget(test_info_widget)




        ################
        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
        #}}}
    #}}}
