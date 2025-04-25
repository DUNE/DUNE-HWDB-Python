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
from PyQt5 import QtCore as qtc

###############################################################################

class SelectPID(zw.PageWidget):
    page_name = "Select PID"
    page_short_name = "Select PID"

    def __init__(self, *args, **kwargs):
        #{{{
        super().__init__(*args, **kwargs)
        
        default_result_msg = "<i>(Enter a PID and click 'find')</i>"

        self.pid_text_box = zw.ZLineEdit(owner=self, key='search_part_id')

        self.completer = qtw.QCompleter(sorted(self.app_state.setdefault('recent_searches', [])))
        self.pid_text_box.setCompleter(self.completer)
        self.find_button = qtw.QPushButton("find")


        self.part_details = zw.ZPartDetails(
                                    owner=self, 
                                    key='part_details',
                                    source='workflow:part_info')
        self.part_details.setMinimumSize(600, 400)

        self.find_button.setStyleSheet(zw.STYLE_SMALL_BUTTON)
        self.find_button.clicked.connect(self.lookup_pid)
        
        self._setup_UI()

        #}}}

    def _setup_UI(self):
        #{{{

        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)

        main_layout.addSpacing(10)

        ##########
        get_pid_layout = qtw.QVBoxLayout()
        get_pid_layout.setContentsMargins(0, 0, 0, 0)
        get_pid_layout.addWidget(qtw.QLabel("Please enter a PID:"))

        search_layout = qtw.QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)


        search_layout.addWidget(self.pid_text_box)
        search_layout.addWidget(self.find_button)

        get_pid_layout.addLayout(search_layout)
        get_pid_layout.addWidget(qtw.QLabel("<i>(Enter a PID and click 'find')</i>"))

        main_layout.addLayout(get_pid_layout)
        main_layout.addSpacing(10)
        ############

        main_layout.addWidget(self.part_details)


        main_layout.addStretch()
        main_layout.addWidget(self.nav_bar)
        self.nav_bar.set_buttons(['continue'])

        self.setLayout(main_layout)

        #}}}

    def lookup_pid(self):
        #{{{

        '''
        def better_message_box(title, icon, text, buttons):
            # QT's stupid QMessageBox().warning(...) puts the freaking
            # dialog box in a random place on the screen. So we have
            # to make our own. Thanks, jerks.
            mw = self.application.main_window
            msgbox = qtw.QMessageBox(mw)
            msgbox.setWindowTitle(title)
            msgbox.setText(text)
            msgbox.setIcon(icon)
            msgbox.setStandardButtons(qtw.QMessageBox.Ok)
            
            mw_geo = mw.frameGeometry()
            msgbox.setGeometry(0, 0, 400, 150)
            msg_geo = msgbox.frameGeometry()

            new_x = mw_geo.x() + (mw_geo.width() - msg_geo.width()) // 2
            new_y = mw_geo.y() + (mw_geo.height() - msg_geo.height()) // 2

            msgbox.move(new_x, new_y)
            return msgbox.exec()
        '''

        part_id = self.page_state['search_part_id']

        with self.wait():
            workflow_state = mdl.download_part_info(
                                    part_id,
                                    refresh=True, # don't use the cache
                                    status_callback=self.application.update_status)

        self.workflow_state.update(workflow_state)

        if not self.part_id:
            
            #better_message_box("Not Found", 
            #                qtw.QMessageBox.Warning,
            #                f"{part_id} was not found.",
            #                qtw.QMessageBox.Ok)

            qtw.QMessageBox.warning(
                            self.application.main_window, 
                            "Not Found", 
                            f"{part_id} was not found.",
                            qtw.QMessageBox.Ok)

            #self.messagebox(
            #            qtw.QMessageBox.warning, 
            #            'Not Found', 
            #            f"{part_id} was not found.", 
            #            qtw.QMessageBox.Ok) # | qtw.QMessageBox.Cancel)

        self.restore() # update dynamic widgets with new data
        self.refresh() # update navigation bar
 
        #}}}
    
    def append_recent_search(self, part_id):
        #{{{
        rs = self.app_state['recent_searches']

        if part_id in rs:
            rs.remove(part_id)
        
        rs.insert(0, part_id)
        rs = rs[:25]

        self.completer = qtw.QCompleter(rs)
        self.pid_text_box.setCompleter(self.completer)
        #}}}

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
        super().restore()

    def refresh(self):
        #{{{
        logger.debug(f"{self.__class__.__name__}.refresh()")
        super().refresh()
        
        if self.part_id:
            self.nav_bar.continue_button.setEnabled(True)
        else:
            self.nav_bar.continue_button.setEnabled(False)

        #}}}




