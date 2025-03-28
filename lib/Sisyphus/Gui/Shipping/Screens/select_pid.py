#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

#{{{
from Sisyphus.Configuration import config, USER_SETTINGS_DIR
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut

from Sisyphus.Gui.Shipping.Widgets import PageWidget, NavBar
from Sisyphus.Gui.Shipping.Widgets import ZLineEdit, ZTextEdit, ZCheckBox, ZLabel

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
    QCompleter,
)

import json
import base64
#}}}

class SelectPID(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        #{{{
        super().__init__(*args, **kwargs)
        
        default_name = self.app_state.setdefault('default_name')
        default_email = self.app_state.setdefault('default_email')
        default_result_msg = "<i>(Enter a PID and click 'find')</i>"

        self.name_text_box = ZLineEdit(owner=self, key='user_name', default=default_name)
        self.email_text_box = ZLineEdit(owner=self, key='user_email', default=default_email)
        
        self.pid_search_result_label = ZLabel(
                    owner=self, key='search_result_message', default=default_result_msg)
        
        self.pid_text_box = ZLineEdit(owner=self, key='search_part_id')

        #self.completer = QCompleter(['D00599800007-00085', 'D00599800007-00084', 'D00599800007-00083'])
        #self.pid_text_box.setCompleter(self.completer)


        self.find_button = QPushButton("find")
        self.find_button.clicked.connect(self.lookup_pid)
        
        self._construct_page()

        #}}}

    def _construct_page(self):
        #{{{

        screen_layout = QVBoxLayout()

        ############
        screen_layout.addWidget(QLabel("Your name:"))
        screen_layout.addWidget(self.name_text_box)
        screen_layout.addSpacing(10)

        ############
        screen_layout.addWidget(QLabel("Your email:"))
        screen_layout.addWidget(self.email_text_box)
        screen_layout.addSpacing(10)

        ##########
        get_pid_layout = QVBoxLayout()
        get_pid_layout.setContentsMargins(0, 0, 0, 0)
        get_pid_layout.addWidget(QLabel("Please enter a PID:"))

        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)


        search_layout.addWidget(self.pid_text_box)
        search_layout.addWidget(self.find_button)
        search_widget = QWidget()
        search_widget.setLayout(search_layout)

        get_pid_layout.addWidget(search_widget)

        get_pid_layout.addWidget(self.pid_search_result_label)

        get_pid_widget = QWidget()
        get_pid_widget.setLayout(get_pid_layout)
        screen_layout.addWidget(get_pid_widget)
        screen_layout.addSpacing(10)
        ############


        screen_layout.addStretch()
        #self.nav_bar = NavBar(self.workflow)
        screen_layout.addWidget(self.nav_bar)
        self.setLayout(screen_layout)

        self.found_pid = None

        #self.restore()
        #}}}

    def lookup_pid(self):
        #{{{
        part_id = self.page_state['search_part_id']

        try:
            item_resp = ut.fetch_hwitems(part_id=part_id)[part_id]
            #print(json.dumps(item_resp, indent=4))

            item_info = item_resp['Item']
            part_type_id = item_info['component_type']['part_type_id']
            part_type_name = item_info['component_type']['name']

            project_id, system_id, subsystem_id = (
                            part_type_id[:1], part_type_id[1:4], part_type_id[4:7])
            
            #print(f"[{project_id}][{system_id}][{subsystem_id}]")

            sys_info = ra.get_system(project_id, system_id)['data']
            #print(json.dumps(sys_info, indent=4))

            subsys_info = ra.get_subsystem(project_id, system_id, subsystem_id)['data']
            #print(json.dumps(subsys_info, indent=4))

            resp_qr = ra.get_hwitem_qrcode(part_id=part_id).content
            part_qr = base64.b85encode(resp_qr).decode('utf-8')
        
        except ra.DatabaseError as exc:
            logger.error(exc)

            msg = f'''<div style="color: #990000">{part_id} not found!</div>'''
            self.pid_search_result_label.setText(msg)

            self.tab_state['part_info'] = None

            self.update() 
            return

        system_name = sys_info['name']
        subsystem_name = subsys_info['subsystem_name']

        part_info = {
            "part_id": part_id,
            "part_type_id": part_type_id,
            "part_type_name": part_type_name,
            'system_id': system_id,
            'system_name': system_name,
            'subsystem_id': subsystem_id,
            'subsystem_name': subsystem_name,
            'qr_code': part_qr,
            'subcomponents': {}
        }

        # Set Subcomponents in tab state
        subcomponent_info = item_resp['Subcomponents']
        for subcomp in subcomponent_info:
            part_info['subcomponents'][subcomp['part_id']] = {
                "Sub-component PID": subcomp['part_id'],
                "Component Type Name": subcomp['type_name'],
                "Functional Position Name": subcomp["functional_position"]
            }

        self.tab_state['part_info'] = part_info
            
        self.page_state['search_result_status'] = 'success'
        
        # self.page_state['search_result_message'] = f'{part_id} found!'
        msg = ''.join([
            "<table>",
            f"<tr><td>Selected PID:</td><td>{part_id}</td></tr>",
            f"<tr><td>Part Type Name:</td><td>{part_type_name}</td></tr>",
            f"<tr><td>System:</td><td>{system_name} ({system_id})</td></tr>",
            f"<tr><td>Subystem:</td><td>{subsystem_name} ({subsystem_id})</td></tr>",
            f"<tr><td>Subcomponents:</td><td>",
            ', '.join([sc['part_id'] for sc in subcomponent_info]),
            f"</td></tr>",
            "</table>",
        ])
        
        self.pid_search_result_label.setText(msg)
       
        self.update() 
        #}}}
    
    def save(self):
        #{{{
        super().save()
        
        self.tab_state['search_part_id'] = self.pid_text_box.text().strip()
        self.tab_state['user_name'] = self.name_text_box.text().strip()
        self.tab_state['user_email'] = self.email_text_box.text().strip()

        if self.tab_state['user_name'] != "":
            #self.parent().app_state.app_state['default_name'] = self.tab_state['user_name']
            self.parent().app.app_state['default_name'] = self.tab_state['user_name']

        if self.tab_state['user_email'] != "":
            #self.parent().app_state.app_state['default_email'] = self.tab_state['user_email']
            self.parent().app.app_state['default_email'] = self.tab_state['user_email']

        self.parent().save()

        #}}}

    def restore(self):
        #{{{
        super().restore()

    def update(self):
        super().update()
        
        self.nav_bar.back_button.setEnabled(False)
        self.nav_bar.back_button.setVisible(False)

        logger.warning(self.tab_state.get('part_info', None))

        if self.tab_state.get('part_info', None) is not None:
            self.nav_bar.continue_button.setEnabled(True)
        else:
            self.nav_bar.continue_button.setEnabled(False)

        #}}}
    #}}}
