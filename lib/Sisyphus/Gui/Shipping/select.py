#!/usr/bin/env python

from Sisyphus.Configuration import config, USER_SETTINGS_DIR
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut

from Sisyphus.Gui.Shipping.application import PageWidget
from Sisyphus.Gui.Shipping.application import ZLineEdit, ZTextEdit, ZCheckBox

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

import json
import base64

class SelectPID(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        #{{{
        super().__init__(*args, **kwargs)

        self.name_text_box = ZLineEdit(parent=self, key='user_name')
        #self.name_text_box.editingFinished.connect(self.save)
        self.email_text_box = ZLineEdit(parent=self, key='user_email')
        #self.name_text_box.editingFinished.connect(self.save)
        
        self.pid_search_result_label = QLabel()
        
        self.pid_text_box = ZLineEdit(parent=self, key='part_id')
        #self.pid_text_box.editingFinished.connect(self.save)

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
        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)
        self.setLayout(screen_layout)

        self.found_pid = None

        #self.restore()
        #}}}

    def lookup_pid(self):
        #{{{
        part_id = self.page_state['part_id']

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

            self.page_state['search_result_status'] = 'fail'
            self.page_state['search_result_message'] = f'{part_id} not found!'


            self.tab_state['part_info'] = None
        
            self.update_search_result_label() 
            self.found_pid = None    # obsolete
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
        self.page_state['search_result_message'] = f'{part_id} found!'

        self.pid_search_result_label.setStyleSheet("color: #0c0;")
        self.pid_search_result_label.setText("Found!")
        self.found_pid = part_id
       
        self.update_search_result_label() 

        self.save()
        #}}}

    def update_search_result_label(self):
        status = self.page_state.get('search_result_status', None)
        message = self.page_state.get('search_result_message', '')

        if status is None:
            color = "#000"
        elif status == 'fail':
            color = "#c00"
        else:
            color = "#0c0"

        self.pid_search_result_label.setStyleSheet(f"color: {color};")
        self.pid_search_result_label.setText(message)

    def save(self):
        #{{{
        print("SAVE: SelectPID")
        self.tab_state['part_id'] = self.pid_text_box.text().strip()
        self.tab_state['user_name'] = self.name_text_box.text().strip()
        self.tab_state['user_email'] = self.email_text_box.text().strip()

        if self.tab_state['user_name'] != "":
            #self.parent().app_state.app_state['default_name'] = self.tab_state['user_name']
            self.parent().app.app_state['default_name'] = self.tab_state['user_name']

        if self.tab_state['user_email'] != "":
            #self.parent().app_state.app_state['default_email'] = self.tab_state['user_email']
            self.parent().app.app_state['default_email'] = self.tab_state['user_email']

        self.parent().save()

        if (self.tab_state['part_id'] == self.found_pid
                and self.tab_state['user_name'] != ''
                and self.tab_state['user_email'] != ''):
            self.nav_bar.continue_button.setEnabled(True)
        else:
            self.nav_bar.continue_button.setEnabled(False)
        #}}}

    def restore(self):
        #{{{
        print("RESTORE: SelectPID")
        #self.pid_text_box.setText(self.tab_state.get('part_id', ""))
        #self.name_text_box.setText(self.tab_state.get('user_name', ""))
        #self.email_text_box.setText(self.tab_state.get('user_email', ""))

        name = self.tab_state.get('user_name', "")
        email = self.tab_state.get('user_email', "")

        if name == "":
            #name = self.parent().app_state._state.get("default_name")
            name = self.parent().app_state.get("default_name", "")
        if email == "":
            #email = self.parent().app_state._state.get("default_email")
            email = self.parent().app_state.get("default_email", "")

        if name != "":
            self.name_text_box.setText(name)
        if email != "":
            self.email_text_box.setText(email)

        self.update_search_result_label()
        self.parent().update_title("Select PID")

        #self.save()
        #}}}
    #}}}

class SelectWorkflow(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.tab_state = self.parent().tab_state

        screen_layout = QVBoxLayout()

        page_title = QLabel("Select Shipping Workflow")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)

        self.radio_packing = QRadioButton("Packing")
        self.radio_preshipping = QRadioButton("Pre-Shipping")
        self.radio_shipping = QRadioButton("Shipping")
        self.radio_transit = QRadioButton("Transit")
        self.radio_receiving = QRadioButton("Receiving")

        self.radio_packing.toggled.connect(self.select_workflow)
        self.radio_preshipping.toggled.connect(self.select_workflow)
        self.radio_shipping.toggled.connect(self.select_workflow)
        self.radio_transit.toggled.connect(self.select_workflow)
        self.radio_receiving.toggled.connect(self.select_workflow)

        self.radio_packing.setEnabled(False)
        self.radio_preshipping.setEnabled(True)
        self.radio_shipping.setEnabled(False)
        self.radio_transit.setEnabled(False)
        self.radio_receiving.setEnabled(False)

        screen_layout.addSpacing(20)
        screen_layout.addWidget(self.radio_packing)
        screen_layout.addWidget(self.radio_preshipping)
        screen_layout.addWidget(self.radio_shipping)
        screen_layout.addWidget(self.radio_transit)
        screen_layout.addWidget(self.radio_receiving)

        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
    def save(self):
        print("SAVE: SelectWorkflow")
        ...

    def restore(self):
        print("RESTORE: SelectWorkflow")
        workflow_type = self.tab_state.get('workflow_type', None)

        if workflow_type == 'packing':
            self.radio_packing.setChecked(True)
        elif workflow_type == 'preshipping':
            self.radio_preshipping.setChecked(True)
        elif workflow_type == 'shipping':
            self.radio_shipping.setChecked(True)
        elif workflow_type == 'transit':
            self.radio_transit.setChecked(True)
        elif workflow_type == 'receiving':
            self.radio_receiving.setChecked(True)
        else:
            self.radio_preshipping.setChecked(True)

        self.parent().update_title(self.tab_state['part_id'])

    def select_workflow(self):
        rb = self.sender()

        if not rb.isChecked():
            # we don't need to do anything for the button that was un-checked
            return

        if rb is self.radio_packing:
            print("packing")
            self.tab_state['workflow_type'] = "packing"
        elif rb is self.radio_preshipping:
            print("preshipping")
            self.tab_state['workflow_type'] = "preshipping"
        elif rb is self.radio_shipping:
            print("shipping")
            self.tab_state['workflow_type'] = "shipping"
        elif rb is self.radio_transit:
            print("transit")
            self.tab_state['workflow_type'] = "transit"
        elif rb is self.radio_receiving:
            print("receiving")
            self.tab_state['workflow_type'] = "receiving"
        else:
            print(f"unknown, {rb}")
            self.tab_state['workflow_type'] = None

        self.save()
    #}}}

