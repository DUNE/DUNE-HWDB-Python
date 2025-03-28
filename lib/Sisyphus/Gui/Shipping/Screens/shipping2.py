#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

#{{{
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
    QFileDialog,
)
#}}}

class Shipping2(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._construct_page()
        self.update()

    def _construct_page(self):
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

        screen_layout.addWidget(self.nav_bar)
        self.setLayout(screen_layout)

    def update(self):
        super().update()
    #}}}
