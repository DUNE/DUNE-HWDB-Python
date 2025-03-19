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


class PreShipping1(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create the interactive widgets on this page

        self.subcomp_caption = QLabel("Contents")

        self.table = QTableWidget(0, 3)
        self.table.verticalHeader().setVisible(False)

        msg = "The list of components for this shipment is correct"
        self.confirm_list_checkbox = ZCheckBox(parent=self, text=msg, key="confirm_list")
        #self.confirm_list_checkbox.toggled.connect(self.toggle_confirm_list)
        

        msg = "All necessary QA/QC information for these components " \
                    "has been stored in the HWDB"
        self.confirm_hwdb_updated_checkbox = ZCheckBox(parent=self, text=msg, key="hwdb_updated")
        #self.confirm_hwdb_updated_checkbox.toggled.connect(self.toggle_hwdb_updated)
        
        # Create the actual layout and place the interactive widgets in it
        self._construct_page()

    def _construct_page(self):
        #{{{
        # This should create the visual appearance of the page. Any widgets
        # that are interactive should be created elsewhere, and then placed
        # inside the layout here. The reason for doing it this way is so
        # that the code creating and controlling dynamic elements won't be
        # cluttered by all the layout code here.

        screen_layout = QVBoxLayout()

        ########################################

        page_title = QLabel("Pre-Shipping Workflow (1)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        
        ########################################

        subcomp_list_layout = QVBoxLayout()
        subcomp_list_layout.addWidget( self.subcomp_caption )
        subcomp_list_layout.addSpacing(5)
        horizontal_header = self.table.horizontalHeader()
        horizontal_header.resizeSection(0, 200)
        horizontal_header.resizeSection(1, 275)
        horizontal_header.resizeSection(2, 275)
        self.table.setHorizontalHeaderLabels(['Sub-component PID',
                            'Component Type Name', 'Functional Position Name'])
        subcomp_list_layout.addWidget(self.table)
        subcomp_list_widget = QWidget()
        subcomp_list_widget.setLayout(subcomp_list_layout)
        screen_layout.addWidget(subcomp_list_widget)
        screen_layout.addSpacing(10)

        ########################################


        screen_layout.addWidget(QLabel("Please affirm the following:"))

        affirm_layout = QHBoxLayout()
        affirm_layout.addSpacing(10)

        indented_layout = QVBoxLayout()
        indented_layout.addWidget(self.confirm_list_checkbox)
        indented_layout.addWidget(self.confirm_hwdb_updated_checkbox)
        indented_widget = QWidget()
        indented_widget.setLayout(indented_layout)
        affirm_layout.addWidget(indented_widget)
        affirm_widget = QWidget()
        affirm_widget.setLayout(affirm_layout)
        screen_layout.addWidget(affirm_widget)

        '''
        confirm_list_layout = QHBoxLayout()
        confirm_list_layout.addWidget( self.confirm_list_checkbox )
        confirm_list_layout.addWidget( QLabel("The list of components for this shipment is correct") )
        confirm_list_layout.addStretch()
        confirm_list_widget = QWidget()
        confirm_list_widget.setLayout(confirm_list_layout)
        screen_layout.addWidget(confirm_list_widget)
        screen_layout.addSpacing(10)

        ########################################

        confirm_hwdb_layout = QHBoxLayout()
        confirm_hwdb_layout.addWidget( self.confirm_hwdb_updated_checkbox )
        confirm_hwdb_layout.addWidget( QLabel("All necessary QA/QC information for these components "
                    "has been stored in the HWDB") )
        confirm_hwdb_layout.addStretch()
        confirm_hwdb_widget = QWidget()
        confirm_hwdb_widget.setLayout(confirm_hwdb_layout)
        screen_layout.addWidget(confirm_hwdb_widget)
        '''

        ########################################

        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
        #}}}

    def toggle_confirm_list(self, status):
        print("toggle confirm list")
        #self.tab_state['pre_shipping_1_confirm_list'] = status
        self.page_state['confirm_list'] = status
        self.save()

    def toggle_hwdb_updated(self, status):
        print("toggle hwdb updated")
        self.tab_state['pre_shipping_1_hwdb_updated'] = status
        self.page_state['hwdb_updated'] = status
        self.save()

    def restore(self):
        setattr(self, "_loading", True)
        super().restore()

        self.populate_subcomps()

        #ch1 = self.page_state.setdefault('confirm_list', False)
        #ch2 = self.page_state.setdefault('hwdb_updated', False)
        #self.confirm_list_checkbox.setChecked(ch1)
        #self.confirm_hwdb_updated_checkbox.setChecked(ch2)
        
        delattr(self, "_loading")

    def save(self):
        if getattr(self, "_loading", False):
            return
        print("SAVE: PreShipping1")
        self.workflow.save()


    def populate_subcomps(self):

        if self.tab_state.get('part_info', None) is None:
            subcomps = {}

        else:
            subcomps = self.tab_state['part_info'].setdefault('subcomponents', {})

        self.table.setRowCount(len(subcomps))
        for idx, subcomp in enumerate(subcomps.values()):
            print(subcomp)
            self.table.setItem(idx, 0, QTableWidgetItem(subcomp['Sub-component PID']))
            self.table.setItem(idx, 1, QTableWidgetItem(subcomp['Component Type Name']))
            self.table.setItem(idx, 2, QTableWidgetItem(subcomp['Functional Position Name']))
    #}}}

