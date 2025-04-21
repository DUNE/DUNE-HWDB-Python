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
from Sisyphus.Gui.Shipping import Model as mdl

from PyQt5 import QtWidgets as qtw

###############################################################################

class SelectPID(zw.PageWidget):
    page_name = "Select PID"
    page_short_name = "Select PID"

    def __init__(self, *args, **kwargs):
        #{{{
        super().__init__(*args, **kwargs)
        
        #default_name = self.app_state.setdefault('default_name')
        #default_email = self.app_state.setdefault('default_email')

        default_result_msg = "<i>(Enter a PID and click 'find')</i>"

        #self.name_text_box = zw.ZLineEdit(owner=self, key='user_name', default=default_name)
        #self.email_text_box = zw.ZLineEdit(owner=self, key='user_email', default=default_email)
        
        self.pid_search_result_label = zw.ZLabel(
                    owner=self, key='search_result_message', default=default_result_msg)
        
        self.pid_text_box = zw.ZLineEdit(owner=self, key='search_part_id')

        self.completer = qtw.QCompleter(sorted(self.app_state.setdefault('recent_searches', [])))
        self.pid_text_box.setCompleter(self.completer)


        self.find_button = qtw.QPushButton("find")
        self.find_button.setStyleSheet(zw.STYLE_SMALL_BUTTON)
        self.find_button.clicked.connect(self.lookup_pid)
        
        self._setup_UI()

        #}}}

    def _setup_UI(self):
        #{{{

        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)

        ############

        '''
        frame = qtw.QFrame()
        frame.setFrameStyle(qtw.QFrame.Box | qtw.QFrame.Sunken)
        frame.setLineWidth(2)

        frame_layout = qtw.QVBoxLayout()
        frame_layout.setContentsMargins(5, 5, 5, 5)

        #main_layout.addWidget(qtw.QLabel("Your name:"))
        #main_layout.addWidget(self.name_text_box)
        #main_layout.addSpacing(10)
        frame_layout.addWidget(qtw.QLabel("Your name:"))
        frame_layout.addWidget(self.name_text_box)
        frame.setLayout(frame_layout)
        main_layout.addWidget(frame)

        ############
        main_layout.addWidget(qtw.QLabel("Your email:"))
        main_layout.addWidget(self.email_text_box)
        '''

        main_layout.addSpacing(10)

        ##########
        get_pid_layout = qtw.QVBoxLayout()
        get_pid_layout.setContentsMargins(0, 0, 0, 0)
        get_pid_layout.addWidget(qtw.QLabel("Please enter a PID:"))

        search_layout = qtw.QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)


        search_layout.addWidget(self.pid_text_box)
        search_layout.addWidget(self.find_button)
        #search_widget = qtw.QWidget()
        #search_widget.setLayout(search_layout)

        #get_pid_layout.addWidget(search_widget)
        get_pid_layout.addLayout(search_layout)

        get_pid_layout.addWidget(self.pid_search_result_label)

        main_layout.addLayout(get_pid_layout)
        main_layout.addSpacing(10)
        ############


        main_layout.addStretch()
        #self.nav_bar = NavBar(self.workflow)
        main_layout.addWidget(self.nav_bar)
        self.setLayout(main_layout)

        #}}}

    def lookup_pid(self):
        #{{{
        part_id = self.page_state['search_part_id']

        with self.wait():
            workflow_state = mdl.download_part_info(part_id,
                            status_callback=self.application.update_status)
        
        if workflow_state is None:
            msg = f'''<div style="color: #990000">{part_id} not found!</div>'''
        else:
            self.append_recent_search(part_id)
            part_info = workflow_state['part_info']
            subcomponent_info = part_info['subcomponents'].values()
            msg = ''.join([
                "<table>",
                f"<tr><td>Selected PID:</td><td>{part_info['part_id']}</td></tr>",
                f"<tr><td>Part Type Name:</td><td>{part_info['part_type_name']}</td></tr>",
                f"<tr><td>System:</td><td>{part_info['system_name']} ({part_info['system_id']})"
                        "</td></tr>",
                f"<tr><td>Subystem:</td><td>{part_info['subsystem_name']} "
                        f"({part_info['subsystem_id']})</td></tr>",
                f"<tr><td>Subcomponents:</td><td>",
                ', '.join([sc['Sub-component PID'] for sc in subcomponent_info]),
                f"</td></tr>",
                "</table>",
            ]) 
            self.workflow_state.update(workflow_state)
        
        self.pid_search_result_label.setText(msg)
        
        self.refresh() 
        #}}}
    
    def append_recent_search(self, part_id):
        rs = self.app_state['recent_searches']

        if part_id in rs:
            rs.remove(part_id)
        
        rs.insert(0, part_id)
        rs = rs[:25]

        self.completer = qtw.QCompleter(rs)
        self.pid_text_box.setCompleter(self.completer)

    def save(self):
        #{{{
        super().save()
        
        self.workflow_state['search_part_id'] = self.pid_text_box.text().strip()

        '''
        self.workflow_state['user_name'] = self.name_text_box.text().strip()
        self.workflow_state['user_email'] = self.email_text_box.text().strip()

        if self.workflow_state['user_name'] != "":
            self.app_state['default_name'] = self.workflow_state['user_name']

        if self.workflow_state['user_email'] != "":
            self.app_state['default_email'] = self.workflow_state['user_email']
        '''


        self.parent().save()

        #}}}

    def restore(self):
        #{{{
        super().restore()

    def refresh(self):
        #{{{
        logger.debug(f"{self.__class__.__name__}.refresh()")
        super().refresh()
        
        self.nav_bar.back_button.setEnabled(False)
        self.nav_bar.back_button.setVisible(False)

        #if self.workflow_state.get('part_info', None) is not None:
        #    self.nav_bar.continue_button.setEnabled(True)
        #else:
        #    self.nav_bar.continue_button.setEnabled(False)

        if self.part_id:
            self.nav_bar.continue_button.setEnabled(True)
        else:
            self.nav_bar.continue_button.setEnabled(False)

        #}}}




