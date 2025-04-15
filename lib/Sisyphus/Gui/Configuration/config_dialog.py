#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config, RESTAPI_DEV, RESTAPI_PROD, DEFAULT_RESTAPI
logger = config.getLogger(__name__)

from Sisyphus.Gui import DataModel as dm
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc

import sys

import json
dumpjson = lambda d: print(json.dumps(d, indent=4))

STYLE_LARGE_BUTTON = """
    font-size: 12pt;
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
       
        # Create the widgets that are interactive in some way.
        # _setup_UI will place them in some orderly way 
        self.profile = qtw.QComboBox()
        self.use_as_default = qtw.QCheckBox("use as default")
        self.delete_profile = qtw.QPushButton("Delete Profile")
        self.rename_profile = qtw.QPushButton("Rename Profile")
        self.new_profile = qtw.QPushButton("New Profile")
        self.server_dev = qtw.QRadioButton(f"Development ({RESTAPI_DEV})")
        self.server_prod = qtw.QRadioButton(f"Production ({RESTAPI_PROD})")
        self.server_other = qtw.QRadioButton("Other")
        self.server_other_text = qtw.QLineEdit()
        server_group = qtw.QButtonGroup()
        server_group.addButton(self.server_dev)
        server_group.addButton(self.server_prod)
        server_group.addButton(self.server_other)
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
        layout.addWidget(self.profile)
        layout.addWidget(self.use_as_default)

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
        layout = server_other_layout = qtw.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.server_other)
        layout.addWidget(self.server_other_text)
        
        layout = server_layout = qtw.QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)
        layout.addWidget(self.server_dev)
        layout.addWidget(self.server_prod)
        layout.addLayout(server_other_layout)

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
        grid_layout.addWidget(qtw.QLabel("(Separate multiple address with a comma)"), 
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
        self.profile.currentIndexChanged.connect(self.on_profile_currentIndexChanged)
        self.use_as_default.stateChanged.connect(self.on_use_as_default_stateChanged)
        self.new_profile.clicked.connect(self.on_new_profile_clicked)
        self.rename_profile.clicked.connect(self.on_rename_profile_clicked)
        self.delete_profile.clicked.connect(self.on_delete_profile_clicked)
        self.server_dev.toggled.connect(self.on_server_dev_toggled)
        self.server_prod.toggled.connect(self.on_server_prod_toggled)
        self.server_other.toggled.connect(self.on_server_other_toggled)
        self.server_other_text.textChanged.connect(self.on_server_other_text_textChanged)

        self.cancel_button.clicked.connect(self.on_cancel_clicked)

    def on_server_dev_toggled(self, status):
        if status:
            self.current_profile['rest api'] = RESTAPI_DEV
            self.server_other_text.setText('')
            self.server_other_text.setEnabled(False)

    def on_server_prod_toggled(self, status):
        if status:
            self.current_profile['rest api'] = RESTAPI_PROD
            self.server_other_text.setText('')
            self.server_other_text.setEnabled(False)

    def on_server_other_toggled(self, status):
        if status:
            self.current_profile['rest api'] = ''
            self.server_other_text.setText('')
            self.server_other_text.setEnabled(True)
    
    def on_server_other_text_textChanged(self):
        if self.server_other.isChecked():
            self.current_profile['rest api'] = self.server_other_text.text()


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

        self.config["profiles"][new_profile_name] = {
            "rest api": DEFAULT_API,
        }

        self.profile.addItem(new_profile_name, new_profile_name)
        self.profile.setCurrentIndex(self.profile.count()-1)
        #}}}            

    def on_profile_currentIndexChanged(self, index):
        #{{{
        print(self.profile.currentData())
        self.use_as_default.blockSignals(True)
        if self.config['default profile'] == self.profile.currentData():
            self.use_as_default.setChecked(True)
            self.use_as_default.setEnabled(False)
        else:
            self.use_as_default.setChecked(False)
            self.use_as_default.setEnabled(True)
        self.use_as_default.blockSignals(False)
        self.populate_profile()
        #}}}

    def on_use_as_default_stateChanged(self, state):
        #{{{
        if state:
            self.config["default_profile"] = self.profile.currentData()
            for index in range(self.profile.count()):
                if index == self.profile.currentIndex():
                    new_text = f"{self.profile.itemData(index)} *"
                else:
                    new_text = self.profile.itemData(index)
                self.profile.setItemText(index, new_text)
            self.use_as_default.setEnabled(False)
        #}}}

    def on_cancel_clicked(self):
        dumpjson(self.config)
        self.close()

    def populate_profile(self):
        #{{{
        current_profile_name = self.profile.currentData()
        current_profile = self.config['profiles'][current_profile_name]

        api = current_profile["rest api"]
        if api == RESTAPI_DEV:
            self.server_dev.setChecked(True)
            self.server_other_text.setEnabled(False)
        elif api == RESTAPI_PROD:
            self.server_prod.setChecked(True)
            self.server_other_text.setEnabled(False)
        else:
            self.server_other.setChecked(True)
            self.server_other_text.setText(api)
            self.server_other_text.setEnabled(True)

            

        #}}}

    @property
    def current_profile_name(self):
        return self.profile.currentData()

    @property
    def current_profile(self):
        return self.config['profiles'][self.current_profile_name]

    @property
    def config(self):
        return config.config_data


    def restore(self):
        #self.whoami = dm.WhoAmI().data

        #dumpjson(self.whoami)
        dumpjson(config.config_data)

        #self.username.setText(whoami["username"])
        #self.user_id.setText(str(whoami["user_id"]))

        default_profile_name = self.config.get("default profile", None)
        profiles = self.config["profiles"]

        if not default_profile_name or default_profile_name not in profiles.keys():
            default_profile_name = self.config["default_profile"] = next(iter(profiles))

        self.profile.blockSignals(True)
        self.profile.clear()
        for profile in profiles:
            if profile != default_profile_name:
                self.profile.addItem(profile, profile)
            else:
                self.profile.addItem(f"{profile} *", profile)

        curr_index = self.profile.findData(default_profile_name)
        self.profile.blockSignals(False)
        self.profile.setCurrentIndex(curr_index)

 


        #active_profile = config.config_data["profiles"][default_profile_name]

        #dumpjson(active_profile)
        

    def save(self):
        ...



