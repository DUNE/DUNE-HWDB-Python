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

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

###############################################################################

class Shipping1(zw.PageWidget):
    page_name = "Shipping Workflow (1)"
    page_short_name = "Shipping (1)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.subcomp_caption = qtw.QLabel("Contents")

        self.part_details = zw.ZPartDetails(
                                    owner=self, 
                                    key='part_details',
                                    source='workflow:part_info')
        self.part_details.setMinimumSize(600, 400)
        
        #self.table = qtw.QTableWidget(0, 3)
        #self.table.verticalHeader().setVisible(False)

        msg = "The list of components for this shipment is correct"
        self.confirm_list_checkbox = zw.ZCheckBox(owner=self, text=msg, key="confirm_list")

        msg = "All necessary QA/QC information for these components " \
                    "has been stored in the HWDB"
        self.confirm_hwdb_updated_checkbox = zw.ZCheckBox(owner=self, text=msg, key="hwdb_updated")

        self._setup_UI()


    def _setup_UI(self):
        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)

        #############################

        subcomp_list_layout = qtw.QVBoxLayout()
        subcomp_list_layout.addWidget( self.subcomp_caption )
        subcomp_list_layout.addSpacing(5)
        
        #horizontal_header = self.table.horizontalHeader()
        #horizontal_header.resizeSection(0, 200)
        #horizontal_header.resizeSection(1, 275)
        #horizontal_header.resizeSection(2, 275)
        #self.table.setHorizontalHeaderLabels(['Sub-component PID',
        #                    'Component Type Name', 'Functional Position Name'])
        #subcomp_list_layout.addWidget(self.table)
        #subcomp_list_widget = qtw.QWidget()
        #subcomp_list_widget.setLayout(subcomp_list_layout)
        #main_layout.addWidget(subcomp_list_widget)
        main_layout.addWidget(self.part_details)
        main_layout.addSpacing(10)

        main_layout.addWidget(qtw.QLabel("Please affirm the following:"))

        affirm_layout = qtw.QHBoxLayout()
        affirm_layout.addSpacing(10)

        indented_layout = qtw.QVBoxLayout()
        indented_layout.addWidget(self.confirm_list_checkbox)
        indented_layout.addWidget(self.confirm_hwdb_updated_checkbox)
        indented_widget = qtw.QWidget()
        indented_widget.setLayout(indented_layout)
        affirm_layout.addWidget(indented_widget)
        affirm_widget = qtw.QWidget()
        affirm_widget.setLayout(affirm_layout)
        main_layout.addWidget(affirm_widget)

        ########################################

        main_layout.addStretch()

        main_layout.addWidget(self.nav_bar)

        self.setLayout(main_layout)

        main_layout.addStretch()

        main_layout.addWidget(self.nav_bar)
        self.setLayout(main_layout)

    def restore(self):
        super().restore()
        #self.populate_subcomps()

    #def populate_subcomps(self):
    #
    #    if self.workflow_state.get('part_info', None) is None:
    #        subcomps = {}
    #
    #    else:
    #        subcomps = self.workflow_state['part_info'].setdefault('subcomponents', {})
    #
    #    self.table.setRowCount(len(subcomps))
    #    for idx, subcomp in enumerate(subcomps.values()):
    #        self.table.setItem(idx, 0, qtw.QTableWidgetItem(subcomp['Sub-component PID']))
    #        self.table.setItem(idx, 1, qtw.QTableWidgetItem(subcomp['Component Type Name']))
    #        self.table.setItem(idx, 2, qtw.QTableWidgetItem(subcomp['Functional Position Name']))

    def refresh(self):
        super().refresh()

        if (self.page_state.get('confirm_list', False)
                    and self.page_state.get('hwdb_updated', False)):
            self.nav_bar.continue_button.setEnabled(True)
        else:
            self.nav_bar.continue_button.setEnabled(False)

