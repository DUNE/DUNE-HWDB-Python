#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config, USER_SETTINGS_DIR
logger = config.getLogger(__name__)  

from Sisyphus.Gui.Shipping import Widgets as zw

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw


class Shipping2(zw.PageWidget):
    page_name = "Shipping Workflow (2)"
    page_short_name = "Shipping (2)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #self.bol_text = ZLineEdit(owner=self, key="bol_filename")
        #self.select_bol_button = QPushButton("Select BoL file")
        #self.select_bol_button.clicked.connect(self.select_bol_dialog)

        self.bol_file = zw.ZFileSelectWidget(owner=self, key='bol_filename')

        self.proforma_container = qtw.QWidget()
        self.proforma_file = zw.ZFileSelectWidget(owner=self, key='proforma_filename')

        self._setup_UI()
        #self.update()

    def _setup_UI(self):
        #{{{
        main_layout = qtw.QVBoxLayout()

        main_layout.addWidget(self.title_bar)
        #############################


        main_layout.addWidget(
                qtw.QLabel("Select Bill of Lading image file:"))
        main_layout.addWidget(self.bol_file)
       
        main_layout.addSpacing(20)
 

        proforma_layout = qtw.QVBoxLayout()
        proforma_layout.setContentsMargins(0, 0, 0, 0)
        self.proforma_container.setLayout(proforma_layout)
        main_layout.addWidget(self.proforma_container)

        #main_layout.addWidget(
        #        QLabel("Select Proforma image file:"))
        #main_layout.addWidget(self.proforma_file)
        proforma_layout.addWidget(
                qtw.QLabel("Select Proforma image file:"))
        proforma_layout.addWidget(self.proforma_file)


        #############################
        main_layout.addStretch()
        main_layout.addWidget(self.nav_bar)
        self.setLayout(main_layout)
        #}}}

    def select_bol_dialog(self):
        file_dialog = qtw.QFileDialog(self)
        file_dialog.setWindowTitle("Select Bill of Lading Image File")

        if file_dialog.exec():
            self.bol_text.setText(file_dialog.selectedFiles()[0])

    def update(self):
        super().update()

        import json
        logger.warning(json.dumps(self.tab_state, indent=4))

        shipping_service_type = self.tab_state.get('PreShipping3a', {}) \
                    .get('shipping_service_type', 'Domestic')

        if shipping_service_type != "International":
            self.proforma_container.setEnabled(False)
            self.page_state['proforma_filename'] = ''
            self.proforma_file.restore()
        else:
            self.proforma_container.setEnabled(True)

        if ( self.page_state.get('bol_filename', '') == ''
                or ( shipping_service_type == 'International' 
                        and self.page_state.get('proforma_filename', '') == '')):
            self.nav_bar.continue_button.setEnabled(False)
        else:
            self.nav_bar.continue_button.setEnabled(True)

    #}}}
