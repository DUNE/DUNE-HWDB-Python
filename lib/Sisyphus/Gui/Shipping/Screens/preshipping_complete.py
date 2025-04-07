#!/usr/bin/env python

#{{{
from Sisyphus.Configuration import config, USER_SETTINGS_DIR
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut

from Sisyphus.Utils.Terminal.Style import Style

from Sisyphus.Gui.Shipping.Widgets import PageWidget, NavBar
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
#}}}

class PreShippingComplete(PageWidget):
    #{{{
    page_name = "Pre-Shipping Workflow Complete"
    page_short_name = "Pre-Shipping Complete"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._setup_UI()
        self.update()
        

    def _setup_UI(self):
        screen_layout = QVBoxLayout()
        ########################################

        page_title = QLabel("Pre-Shipping Workflow Complete")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        ################

        screen_layout.addSpacing(30)

        screen_layout.addWidget(
                QLabel("This workflow is finished. You may close this tab."))


        screen_layout.addStretch()

        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)


    def update(self):
        self.nav_bar.back_button.setEnabled(False)
        self.nav_bar.continue_button.setEnabled(False)


    #}}}



