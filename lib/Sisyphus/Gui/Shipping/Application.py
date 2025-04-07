#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config, USER_SETTINGS_DIR
logger = config.getLogger(__name__)

HLD = highlight = "[bg=#999999,fg=#ffffff]"
HLI = highlight = "[bg=#009900,fg=#ffffff]"
HLW = highlight = "[bg=#999900,fg=#ffffff]"
HLE = highlight = "[bg=#990000,fg=#ffffff]"

import Sisyphus
from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus.Gui.Shipping.WorkflowWidget import WorkflowWidget
from Sisyphus.Gui.Shipping.MainWindow import MainWindow

from PyQt5 import QtWidgets as qtw

from pathlib import Path
import sys, os
import json
from datetime import datetime

from uuid import uuid4
import qdarkstyle

class Application(qtw.QApplication):
    #{{{
    def __init__(self, argv=[]):
        super().__init__(argv)

        self._debug = ("--debug" in argv)
        self._force_reset = ("--reset" in argv)

        if True:
            try:
                style_path = Sisyphus.get_path('resources/style.qss')
                self.setStyleSheet(Path(style_path).read_text())
            except FileNotFoundError as exc:
                msg = "Stylesheet not found. Using default style."
                Style.error.print(msg)
                logger.error(msg)
        else:
            dark_stylesheet = qdarkstyle.load_stylesheet_pyqt5()
            self.setStyleSheet(dark_stylesheet)

        self.application_state_path = os.path.normpath(
                    os.path.join(config.user_settings_dir, "shipping_conf.json"))

        self.load_state()

        self.main_window = MainWindow(application=self)
        self.tab_widget = self.main_window.tab_widget

        self.restore_tabs()

    def reset_state(self):
        logger.warn("Resetting shipping application state") 
        self.app_state = {
            "working_directory": os.path.normpath(os.path.expanduser('~/.sisyphus/shipping')),
            "tabs": [],
            "current_tab": -1,
            "workflows": {},
        }
        #self.create_tab()

    def validate_state(self):
        if not self.app_state.get('working_directory'):
            return False
        if type(self.app_state.get('tabs')) is not list:
            return False
        if type(self.app_state.get('workflows')) is not dict: 
            return False

        return True

    def load_state(self):
        #{{{
        logger.debug("Loading application state")

        if self._force_reset:
            msg = ("The application state is being reset by request.")
            Style.info.print(msg)
            logger.info(msg)

            self.reset_state()
            return

        try:
            with open(self.application_state_path, 'r') as fp:
                self.app_state = json.load(fp)
        except FileNotFoundError as exc:
            # not found = this is the first run. No problem.
            # just create the file.
            msg = ("This appears to be the first time the application is being run.")
            Style.info.print(msg)
            logger.info(msg)
            self.reset_state()
            return

        except json.JSONDecodeError as exc:
            # some other error. assume the file is corrupt
            # and overwrite it.
            msg = ("The application state appears to be corrupted. "
                        "Starting with fresh application state.")
            Style.error.print(msg)
            logger.error(f"{type(exc)}: {exc}")
            logger.error(msg)

            self.reset_state()
            return

        if not self.validate_state():
            # check that the state is structured correctly. 
            # This is likely due to changes in the code that require
            # things to be different than the last time the app was run
            msg = ("The application state is not compatible with the current version. "
                        "Starting with fresh application state.")
            Style.error.print(msg)
            logger.error(msg)
            
            self.reset_state()
            return
            


        #if "working_directory" not in self.app_state:
        #    wd = os.path.normpath(os.path.expanduser('~/.sisyphus/shipping'))
        #    self.app_state["working_directory"] = wd
        #else:
        #    wd = os.path.normpath(os.path.expanduser(self.app_state['working_directory']))
        #os.makedirs(wd, exist_ok=True)
        #}}}

    def save_state(self):
        logger.debug("Saving application state")
        '''
        all_tabs_state = []
        for idx in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(idx)
            tab_state = tab.tab_state
            all_tabs_state.append(tab_state)

        self.app_state['tabs'] = all_tabs_state
        self.app_state['current_tab'] = self.tab_widget.currentIndex()
        '''
        self.app_state['current_tab'] = self.tab_widget.currentIndex()

        recent_saves = self.app_state.setdefault('recent_saves', [])
        recent_saves.insert(0, datetime.now().isoformat())
        while len(recent_saves)>10:
            recent_saves.pop()
        with open(self.application_state_path, 'w') as fp:
            json.dump(self.app_state, fp, indent=4)


    def restore_tabs(self):
        logger.info(f"restoring tabs")
        while self.tab_widget.count():
            self.tab_widget.removeTab(0)
        
        curr_idx = self.app_state.get('current_tab', 0)

        for tab_index in range(len(self.app_state['tabs'])):
            self.restore_tab(tab_index=tab_index)

        #curr_idx = self.app_state.get('current_tab', 0)
        if self.tab_widget.count() > 0:
            logger.info(f"setting current tab: {curr_idx}")
            self.tab_widget.setCurrentIndex(curr_idx)

    def restore_tab(self, *, tab_index=None):
        logger.info(f"restoring tab {tab_index}")
        if tab_index is None:
            raise ValueError("required parameter: tab_index")

        workflow_uuid = self.app_state['tabs'][tab_index]
        tab_state = self.app_state['workflows'][workflow_uuid]

        restored_workflow = WorkflowWidget(owner=self, uuid=workflow_uuid)
        logger.info(f"finished_init: {restored_workflow._finished_init}")
        self.tab_widget.addTab(restored_workflow, "uninitialized")
        #restored_workflow.update_tab_title()
        restored_workflow.activate()
        #restored_workflow.current_page_widget.activate()
        
    def create_new_tab(self, *, tab_state=None):
        logger.info(f"{self.__class__.__name__}.create_new_tab()")
        new_uuid = uuid4().hex      
        if tab_state is None:
            tab_state = {
                'uuid': new_uuid,
                'current_page': "SelectPID",
            }
        elif tab_state.get('uuid') is None:
            tab_state['uuid'] = new_uuid

        self.app_state['workflows'][new_uuid] = tab_state
        self.app_state['tabs'].append(new_uuid)

        new_workflow = WorkflowWidget(owner=self, uuid=new_uuid)
        logger.info(f"finished_init: {new_workflow._finished_init}")
        self.tab_widget.addTab(new_workflow, "new workflow")
        new_workflow.update_tab_title()
        #new_workflow.current_page_widget.activate()
        new_workflow.activate()

        idx = self.tab_widget.indexOf(new_workflow)
        self.tab_widget.setCurrentIndex(idx)

    def close_tab(self, tab_index):
        current_widget = self.tab_widget.widget(tab_index)

        if isinstance(current_widget, WorkflowWidget):
            workflow_uuid = current_widget.uuid
            self.app_state['tabs'].remove(workflow_uuid)
            del self.app_state['workflows'][workflow_uuid]

        current_widget.deleteLater()
        self.tab_widget.removeTab(tab_index)

    def on_currentChanged(self, tab_index):
        self.app_state['current_tab'] = tab_index
        
    @property
    def working_directory(self):
        return self.app_state.get("working_directory", os.path.normpath('.'))


    def update_status(self, message):
        #self.main_window.status_bar.showMessage(message, timeout=10)
        #self.main_window.status_bar.showMessage(message)
        Style.notice.print(f"status bar: {message}")

    def configure(self):
        Style.info.print("Configuration not implemented yet")

    def debug_app_state(self):
        Style.info.print("APP_STATE")
        Style.info.print(json.dumps(self.app_state, indent=4))
    
    def debug_tab_tree(self):
        Style.info.print("APP_STATE")
        
        tab_index = self.tab_widget.currentIndex()
        workflow_widget = self.tab_widget.currentWidget()
        page_widget = workflow_widget.current_page_widget

        Style.info.print(f"current tab index: {tab_index}")
        Style.info.print(f"current tab widget: {workflow_widget.uuid}")
        Style.info.print(f"current tab widget: {page_widget.__class__.__name__}")

        #Application.widget_tree(self.tab_widget)
        Application.widget_tree(self.main_window)

    def debug_page_tree(self):
        Style.info.print("TAB_STATE")

        tab_index = self.tab_widget.currentIndex()
        workflow_widget = self.tab_widget.currentWidget()
        page_widget = workflow_widget.current_page_widget

        Style.info.print(f"current tab index: {tab_index}")
        Style.info.print(f"current tab widget: {workflow_widget.uuid}")
        Style.info.print(f"current tab widget: {page_widget.__class__.__name__}")

        Application.widget_tree(page_widget)

    @staticmethod
    def widget_tree(widget):
        def widget_details(widget):
            txt = [widget.__class__.__name__]
            if isinstance(widget, (qtw.QLabel, qtw.QPushButton, 
                                qtw.QRadioButton, qtw.QCheckBox)):
                txt.append(f'"{widget.text()}"')

            return ' '.join(txt)

        def widget_info(widget):
            def list_children(widget, indent_level=0):
                children = widget.findChildren(qtw.QWidget)
                for child in children:
                    if child.parent() != widget:
                        continue
                    indent = "    " * indent_level
                    print(f"{indent}{widget_details(child)}")
                    list_children(child, indent_level+1)

            print(widget_details(widget))
            list_children(widget, indent_level=1)
        widget_info(widget)

    def debug_test_function(self):
        
        new_widget = qtw.QLabel("Test Widget")
        self.tab_widget.addTab(new_widget, "Test!")

    def exit(self):
        logger.warning(f"{HLW}{self.__class__.__name__}.exit(): quitting aplication")
        self.save_state()
        self.main_window.close()
    #}}}
