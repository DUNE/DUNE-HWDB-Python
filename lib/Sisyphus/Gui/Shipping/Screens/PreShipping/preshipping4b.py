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
from Sisyphus.Gui.Shipping.Widgets.PageWidget import PageWidget

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

###############################################################################

class PreShipping4b(PageWidget):
    page_name = "Pre-Shipping Workflow (4b)"
    page_short_name = "Pre-Shipping (4b)"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.freight_forwarder = zw.ZLineEdit(page=self, key='freight_forwarder')
        self.mode_of_transportation = zw.ZLineEdit(page=self, key='mode_of_transportation')
        self.expected_arrival_time = zw.ZDateTimeEdit(page=self, key='expected_arrival_time')
        

        self._setup_UI()

    def _setup_UI(self):
        #{{{
        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)

        ########################################

        self.mess_label = qtw.QLabel(
                "Provide name(s) of your Freight Forwarder (FF; such as FedEx or UPS. "
                "USPS is not allowed) and mode(s) of transportation (truck, air, ship, "
                "rail, etc.):"
        )
        self.mess_label.setWordWrap(True)
        main_layout.addWidget(self.mess_label)

        ff_mode_layout = qtw.QVBoxLayout()

        ff_layout = qtw.QHBoxLayout()
        self.ff_label = qtw.QLabel("Name of FF:")
        ff_layout.addWidget(self.ff_label)
        ff_layout.addWidget( self.freight_forwarder )
        ff_widget = qtw.QWidget()
        ff_widget.setLayout(ff_layout)

        mode_layout = qtw.QHBoxLayout()
        self.mode_label = qtw.QLabel("Mode:")
        mode_layout.addWidget( self.mode_label )
        mode_layout.addWidget( self.mode_of_transportation )
        mode_widget = qtw.QWidget()
        mode_widget.setLayout(mode_layout)

        ff_mode_layout.addWidget(ff_widget)
        ff_mode_layout.addWidget(mode_widget)
        ff_mode_widget = qtw.QWidget()
        ff_mode_widget.setLayout(ff_mode_layout)

        main_layout.addWidget(ff_mode_widget)

        ################

        main_layout.addSpacing(10)


        self.time_label = qtw.QLabel("Provide the expected arrival time (Central Time):")
        main_layout.addWidget(self.time_label)
        main_layout.addWidget( self.expected_arrival_time)


        ################

        main_layout.addStretch()

        main_layout.addWidget(self.nav_bar)

        self.setLayout(main_layout)
        #}}}

    def refresh(self):
        super().refresh()

        # --- dynamically show/hide things ---
        select_pid_state = self.workflow_state.get("SelectPID", {})
        is_surf = select_pid_state.get("confirm_surf", False)
        if not is_surf:
            self.mess_label.hide()
            self.ff_label.hide()
            self.freight_forwarder.hide()
            self.mode_label.hide()
            self.mode_of_transportation.hide()
            self.time_label.hide()
            self.expected_arrival_time.hide()
        else:
            self.mess_label.show()
            self.ff_label.show()
            self.freight_forwarder.show()
            self.mode_label.show()
            self.mode_of_transportation.show()
            self.time_label.show()
            self.expected_arrival_time.show()


        if is_surf:
            if (
                    len(self.freight_forwarder.text()) > 0
                    and len(self.mode_of_transportation.text()) > 0):
                self.nav_bar.continue_button.setEnabled(True)
            else:
                self.nav_bar.continue_button.setEnabled(False)
        else:
            self.nav_bar.continue_button.setEnabled(True)
