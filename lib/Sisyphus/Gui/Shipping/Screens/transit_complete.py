#!/usr/bin/env python

from Sisyphus.Gui.Shipping.Widgets import PageWidget, NavBar

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
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtGui import QIcon

class TransitComplete(PageWidget):
    #{{{
    page_name = "Transit Workflow Complete"
    page_short_name = "Transit Complete"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        screen_layout = QVBoxLayout()
        ########################################

        page_title = QLabel("Transit Workflow Complete")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        ################
        screen_layout.addStretch()

        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
    #}}}

