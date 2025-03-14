#!/usr/bin/env python

from Sisyphus.Gui.Shipping.application import PageWidget

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

class Shipping1(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        screen_layout = QVBoxLayout()

        #############################
        page_title = QLabel("Shipping Workflow (1)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        #############################

        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)
        self.setLayout(screen_layout)
    #}}}

class Shipping2(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        screen_layout = QVBoxLayout()

        #############################
        page_title = QLabel("Shipping Workflow (2)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        #############################

        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)
        self.setLayout(screen_layout)
    #}}}

class Shipping3(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)
        self.setLayout(screen_layout)
    #}}}

class Shipping4(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        screen_layout = QVBoxLayout()

        #############################
        page_title = QLabel("Shipping Workflow (4)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        #############################

        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)
        self.setLayout(screen_layout)
    #}}}

class ShippingComplete(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        screen_layout = QVBoxLayout()

        #############################
        page_title = QLabel("Shipping Workflow Complete")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        #############################

        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)
        self.setLayout(screen_layout)
    #}}}

