#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus.Gui.Shipping import Widgets as zw

from PyQt5 import QtWidgets as qtw

class Receiving1(zw.PageWidget):
    page_name = "Receiving Workflow (1)"
    page_short_name = "Receiving (1)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create the interactive widgets on this page

        self.subcomp_caption = qtw.QLabel("Contents")

        self.part_details = zw.ZPartDetails(
                                    page=self, 
                                    key='part_details',
                                    source='workflow:part_info')
        self.part_details.setMinimumSize(600, 400)

        msg = "The list of components for this shipment is correct"
        self.confirm_list_checkbox = zw.ZCheckBox(page=self, text=msg, key="confirm_list")
        
        self._setup_UI()

    def _setup_UI(self):
        #{{{
        # This should create the visual appearance of the page. Any widgets
        # that are interactive should be created elsewhere, and then placed
        # inside the layout here. The reason for doing it this way is so
        # that the code creating and controlling dynamic elements won't be
        # cluttered by all the layout code here.

        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)
        ########################################

        #subcomp_list_layout = qtw.QVBoxLayout()
        #subcomp_list_layout.addWidget( self.subcomp_caption )
        #subcomp_list_layout.addSpacing(5)
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

        ########################################


        main_layout.addWidget(qtw.QLabel("Please affirm the following:"))

        affirm_layout = qtw.QHBoxLayout()
        affirm_layout.addSpacing(10)

        indented_layout = qtw.QVBoxLayout()
        indented_layout.addWidget(self.confirm_list_checkbox)
        #indented_layout.addWidget(self.confirm_hwdb_updated_checkbox)
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
        #}}}

    def refresh(self):
        super().refresh()

        if self.page_state.get('confirm_list', False):
            self.nav_bar.continue_button.setEnabled(True)
        else:
            self.nav_bar.continue_button.setEnabled(False)

