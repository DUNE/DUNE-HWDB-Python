#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config, RESTAPI_DEV, RESTAPI_PROD, DEFAULT_RESTAPI
#from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

import Sisyphus.Configuration as cfg # for keywords
from Sisyphus.Gui import DataModel as dm
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc

import sys
from copy import deepcopy
import os
import json

STYLE_LARGE_BUTTON = """
    font-size: 15pt;
    padding: 5px 15px;
"""

STYLE_SMALL_BUTTON = """
    padding: 5px 15px;
"""

class ConfigDialog(qtw.QDialog):
    def __init__(self, *args, **kwargs):
        #{{{
        #super().__init__(*args, **kwargs)
        super().__init__()
        # Grab a copy of the config state as it is right now.
        # We will need it if the user cancels their changes.
        self._backup_config_data = deepcopy(config.config_data)

        # Create the widgets that are interactive in some way.
        # _setup_UI will place them in some orderly way 
        self.select_profile = qtw.QComboBox()
        self.set_active = qtw.QCheckBox("set active")
        self.delete_profile = qtw.QPushButton("Delete Profile")
        self.rename_profile = qtw.QPushButton("Rename Profile")
        self.new_profile = qtw.QPushButton("New Profile")

        self.servers = {}
        self.servers_by_name = {}

        self.server_group = qtw.QButtonGroup()
        for server_name, server_url in self.config[cfg.KW_SERVERS].items():
            radio_button = qtw.QRadioButton(f"{server_name} ({server_url})")
            self.servers_by_name[server_name] = {
                "server_name": server_name,
                "server_url": server_url,
                "radio_button": radio_button
            }
            self.servers[radio_button] = self.servers_by_name[server_name]
            self.server_group.addButton(radio_button)

        self.username = qtw.QLineEdit()
        self.user_id = qtw.QLineEdit()
        self.username.setEnabled(False)
        self.user_id.setEnabled(False)
        self.full_name = qtw.QLineEdit()
        self.full_name_sync = qtw.QCheckBox("sync with HWDB")
        self.email = qtw.QLineEdit()
        self.email_sync = qtw.QCheckBox("sync with HWDB")
        self.working_directory = qtw.QLineEdit()
        self.working_directory_select = qtw.QPushButton("choose directory")
        self.cancel_button = qtw.QPushButton("Cancel")
        self.save_button = qtw.QPushButton("Save")

        # Arrange the interactive widgets (in some orderly way)
        self._setup_UI()

        # Make some connections
        self._setup_connections()
        
        self.restore()
        #}}}

    def _setup_UI(self):
        #{{{
        self.setWindowTitle("HWDB Configuration")
        self.setMinimumSize(640, 480)

        #######################
        #
        #  PROFILE
        #
        #######################

        layout = profile_select_layout = qtw.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.select_profile)
        layout.addWidget(self.set_active)

        layout = profile_buttons_layout = qtw.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(self.delete_profile)
        layout.addWidget(self.rename_profile)
        layout.addWidget(self.new_profile)
        for btn in (self.delete_profile, self.rename_profile, self.new_profile):
            btn.setStyleSheet(STYLE_SMALL_BUTTON)
        layout.addStretch()
       
        layout = profile_layout = qtw.QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        layout.addLayout(profile_select_layout)
        layout.addLayout(profile_buttons_layout)

        frame = profile_frame = qtw.QFrame()
        frame.setFrameStyle(qtw.QFrame.Box | qtw.QFrame.Sunken)
        frame.setLineWidth(1)
        frame.setLayout(profile_layout)
        
 
        #######################
        #
        #  SERVER
        #
        #######################
        #layout = server_other_layout = qtw.QHBoxLayout()
        #layout.setContentsMargins(0, 0, 0, 0)
        #layout.addWidget(self.server_other)
        #layout.addWidget(self.server_other_text)
        
        layout = server_layout = qtw.QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)
        for radio_button, server_details in self.servers.items():
            layout.addWidget(radio_button)
        #layout.addWidget(self.server_dev)
        #layout.addWidget(self.server_prod)
        #layout.addLayout(server_other_layout)

        frame = server_frame = qtw.QFrame()
        frame.setFrameStyle(qtw.QFrame.Box | qtw.QFrame.Sunken)
        frame.setLineWidth(1)
        frame.setLayout(server_layout)

        #######################
        #
        #  USER INFO
        #
        #######################
        layout = full_name_layout = qtw.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.full_name)
        layout.addWidget(self.full_name_sync)

        layout = email_layout = qtw.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.email)
        layout.addWidget(self.email_sync)

        layout = directory_layout = qtw.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.working_directory)
        layout.addWidget(self.working_directory_select)
        self.working_directory_select.setStyleSheet(STYLE_SMALL_BUTTON)
        self.working_directory.setEnabled(False)
       
        #######################
        #
        #  SAVE/CANCEL BUTTONS
        #
        #######################
        button_layout = qtw.QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        for btn in (self.cancel_button, self.save_button):
            btn.setStyleSheet(STYLE_LARGE_BUTTON)

        #######################
        #
        #  ARRANGE LAYOUT
        #
        #######################

        main_layout = qtw.QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(main_layout)

        grid_layout = qtw.QGridLayout()
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 3)
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(0)
        main_layout.addLayout(grid_layout)

        top_right = qtc.Qt.AlignTop | qtc.Qt.AlignRight
        top_left = qtc.Qt.AlignTop | qtc.Qt.AlignLeft
        center_right = qtc.Qt.AlignVCenter | qtc.Qt.AlignRight
        center_left = qtc.Qt.AlignVCenter | qtc.Qt.AlignLeft
        top_center = qtc.Qt.AlignTop | qtc.Qt.AlignHCenter

        current_row = 0
        grid_layout.addWidget(qtw.QLabel("Profile"), 
                            current_row, 0, 1, 1, top_right)
        grid_layout.addWidget(profile_frame,
                            current_row, 1, 1, 1)

        current_row += 1
        grid_layout.setRowMinimumHeight(current_row, 10)

        current_row += 1
        grid_layout.addWidget(qtw.QLabel("Server"), 
                            current_row, 0, 1, 1, top_right)
        grid_layout.addWidget(server_frame, 
                            current_row, 1, 1, 1)
        
        current_row += 1
        grid_layout.setRowMinimumHeight(current_row, 10)
        
        current_row += 1
        grid_layout.addWidget(qtw.QLabel("Username"), 
                            current_row, 0, 1, 1, center_right)
        grid_layout.addWidget(self.username, 
                            current_row, 1, 1, 1, center_left)
        
        current_row += 1
        grid_layout.setRowMinimumHeight(current_row, 10)

        current_row += 1
        grid_layout.addWidget(qtw.QLabel("User ID"), 
                            current_row, 0, 1, 1, center_right)
        grid_layout.addWidget(self.user_id, 
                            current_row, 1, 1, 1, center_left)

        current_row += 1
        grid_layout.setRowMinimumHeight(current_row, 10)
        
        current_row += 1
        grid_layout.addWidget(qtw.QLabel("Full Name"), 
                            current_row, 0, 1, 1, center_right)
        grid_layout.addLayout(full_name_layout, 
                            current_row, 1, 1, 1)

        current_row += 1
        grid_layout.setRowMinimumHeight(current_row, 10)
        
        current_row += 1
        grid_layout.addWidget(qtw.QLabel("Email Address"), 
                            current_row, 0, 1, 1, center_right)
        grid_layout.addLayout(email_layout, 
                            current_row, 1, 1, 1, center_left)
        
        current_row += 1
        widget = qtw.QLabel("(Separate multiple address with a comma)")
        widget.setEnabled(False) # really, just to make it look grey
        grid_layout.addWidget(widget, 
                            current_row, 1, 1, 1, top_left)
        
        current_row += 1
        grid_layout.setRowMinimumHeight(current_row, 10)
        
        current_row += 1
        grid_layout.addWidget(qtw.QLabel("Working Directory"), 
                            current_row, 0, 1, 1, center_right)
        grid_layout.addLayout(directory_layout, 
                            current_row, 1, 1, 1)
        
        main_layout.addStretch()
        main_layout.addLayout(button_layout)
        #}}}

    def _setup_connections(self):
        self.select_profile.currentIndexChanged.connect(self.on_select_profile_currentIndexChanged)
        self.set_active.stateChanged.connect(self.on_set_active_stateChanged)
        self.new_profile.clicked.connect(self.on_new_profile_clicked)
        self.rename_profile.clicked.connect(self.on_rename_profile_clicked)
        self.delete_profile.clicked.connect(self.on_delete_profile_clicked)
        
        for radio_button, server_details in self.servers.items():
            radio_button.toggled.connect(self.on_server_toggled)

        self.full_name.textChanged.connect(self.on_full_name_textChanged)
        self.email.textChanged.connect(self.on_email_textChanged)
        self.full_name_sync.toggled.connect(self.on_full_name_sync_toggled)
        self.email_sync.toggled.connect(self.on_email_sync_toggled)
        self.working_directory.textChanged.connect(self.on_working_directory_textChanged)
        self.working_directory_select.clicked.connect(self.on_working_directory_select_clicked)
        self.cancel_button.clicked.connect(self.on_cancel_button_clicked)
        self.save_button.clicked.connect(self.on_save_button_clicked)

    def on_server_toggled(self, status):
        if status:
            sender = self.sender()
            server_details = self.servers[sender]
            self.current_profile[cfg.KW_RESTAPI_NAME] = server_details['server_name']
            self.current_profile[cfg.KW_RESTAPI] = server_details['server_url']
            

    def on_rename_profile_clicked(self):
        #{{{
        ret = qtw.QMessageBox().information(
                        self, 
                        "Info",
                        f"Not implemented.",
                        qtw.QMessageBox.Ok)
        #}}}

    def on_delete_profile_clicked(self):
        #{{{
        ret = qtw.QMessageBox().information(
                        self, 
                        "Info",
                        f"Not implemented.",
                        qtw.QMessageBox.Ok)
        #}}}

    def on_new_profile_clicked(self):
        #{{{
        new_profile_name, ok = qtw.QInputDialog().getText(
                                self,
                                "Enter New Profile Name",
                                "Profile Name:",
                                qtw.QLineEdit.Normal,
                                "")
        if not ok:
            return

        new_profile_name = new_profile_name.strip()
        if len(new_profile_name) == 0:
            return

        if new_profile_name in self.config["profiles"]:
            ret = qtw.QMessageBox().critical(
                                self, 
                                "Error",
                                f"The profile '{new_profile_name}' already exists.",
                                qtw.QMessageBox.Ok)
            return

        self.config["profiles"][new_profile_name] = deepcopy(cfg.NEW_PROFILE)

        self.select_profile.addItem(new_profile_name, new_profile_name)
        self.select_profile.setCurrentIndex(self.select_profile.count()-1)
        #}}}            

    def on_select_profile_currentIndexChanged(self, index):
        self.populate_profile()

    def on_set_active_stateChanged(self, state):
        #{{{
        if state:
            self.config[cfg.KW_ACTIVE_PROFILE] = self.select_profile.currentData()
            for index in range(self.select_profile.count()):
                if index == self.select_profile.currentIndex():
                    new_text = f"{self.select_profile.itemData(index)} *"
                else:
                    new_text = self.select_profile.itemData(index)
                self.select_profile.setItemText(index, new_text)
            self.set_active.setEnabled(False)
        #}}}

    def on_cancel_button_clicked(self):
        # TODO: are you sure?
        config.config_data = self._backup_config_data
        self.close()

    def on_save_button_clicked(self):
        config.save()
        self.close()


    @property
    def current_profile(self):
        return self.config['profiles'][self.select_profile.currentData()]

    @property
    def current_profile_name(self):
        return self.select_profile.currentData()

    def populate_profile(self):
        #{{{
        server_name = self.current_profile[cfg.KW_RESTAPI_NAME]
        editable = self.current_profile[cfg.KW_RESTAPI_EDITABLE]

        self.set_active.blockSignals(True)
        if self.config[cfg.KW_ACTIVE_PROFILE] == self.select_profile.currentData():
            self.set_active.setChecked(True)
            self.set_active.setEnabled(False)
        else:
            self.set_active.setChecked(False)
            self.set_active.setEnabled(True)
        self.set_active.blockSignals(False)

        for radio_button, server_details in self.servers.items():
            if server_name == server_details['server_name']:
                radio_button.setChecked(True)
            else:
                radio_button.setChecked(False)
            if editable:
                radio_button.setEnabled(True)
            else:
                radio_button.setEnabled(False)

        
        profile_obj = config.get_profile(self.current_profile_name)
        self.hwdb_user_data = dm.WhoAmI(profile=profile_obj).data

        username = self.hwdb_user_data["username"]
        user_id = self.hwdb_user_data["user_id"]

        self.username.setText(username)
        self.user_id.setText(str(user_id))


        self.user_node = self.current_profile.setdefault('users', {}).setdefault(username, {})
        user_node = self.user_node
        user_node.setdefault("full_name", None)
        user_node.setdefault("email", None)
        user_node.setdefault("working_directory", os.path.expanduser('~'))

        self.full_name.blockSignals(True)
        self.email.blockSignals(True)
        self.full_name.setText(user_node['full_name'] or self.hwdb_user_data['full_name']) 
        self.email.setText(user_node['email'] or self.hwdb_user_data['email']) 
        self.full_name.blockSignals(False)
        self.email.blockSignals(False)

        self.full_name.setEnabled(user_node['full_name'] is not None)
        self.email.setEnabled(user_node['email'] is not None)
        self.full_name_sync.setChecked(user_node['full_name'] is None)
        self.email_sync.setChecked(user_node['email'] is None)

        self.working_directory.setText(user_node['working_directory'])
        

        #}}}

    def on_full_name_textChanged(self):
        self.user_node['full_name'] = self.full_name.text()
    
    def on_full_name_sync_toggled(self, status):
        self.full_name.blockSignals(True)
        if status:
            self.full_name.setEnabled(False)
            self.full_name.setText(self.hwdb_user_data['full_name'])
            self.user_node['full_name'] = None
        else:
            self.full_name.setEnabled(True)
            self.user_node['full_name'] = self.full_name.text()
        self.full_name.blockSignals(False)
           
    def on_email_textChanged(self):
        self.user_node['email'] = self.email.text()
    
    def on_email_sync_toggled(self, status):
        self.email.blockSignals(True)
        if status:
            self.email.setEnabled(False)
            self.email.setText(self.hwdb_user_data['email'])
            self.user_node['email'] = None
        else:
            self.email.setEnabled(True)
            self.user_node['email'] = self.email.text()
        self.email.blockSignals(False)

    def on_working_directory_textChanged(self):
        self.user_node['working_directory'] = self.working_directory.text()

    def on_working_directory_select_clicked(self):
        filename = qtw.QFileDialog.getExistingDirectory(
                            self,
                            "Select Working Directory",
                            self.user_node['working_directory'])
        if filename != "":
            self.working_directory.setText(filename)

    @property
    def current_profile_name(self):
        return self.select_profile.currentData()

    @property
    def current_profile(self):
        return self.config[cfg.KW_PROFILES][self.current_profile_name]

    @property
    def config(self):
        return config.config_data


    def restore(self):

        default_profile_name = self.config.get(cfg.KW_ACTIVE_PROFILE, None)
        profiles = self.config[cfg.KW_PROFILES]

        if not default_profile_name or default_profile_name not in profiles.keys():
            default_profile_name = self.config[cfg.KW_ACTIVE_PROFILE] = next(iter(profiles))

        self.select_profile.blockSignals(True)
        self.select_profile.clear()
        for profile in profiles:
            if profile != default_profile_name:
                self.select_profile.addItem(profile, profile)
            else:
                self.select_profile.addItem(f"{profile} *", profile)

        curr_index = self.select_profile.findData(default_profile_name)
        self.select_profile.setCurrentIndex(curr_index)
        self.select_profile.blockSignals(False)

        self.populate_profile()


