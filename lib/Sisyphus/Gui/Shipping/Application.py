#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus.Gui.Shipping.Widgets.WorkflowWidget import WorkflowWidget
from Sisyphus.Gui.Shipping.Widgets.MainWindow import MainWindow
from Sisyphus.Gui.Configuration import ConfigDialog
from Sisyphus.Gui import DataModel as dm

from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc

from pathlib import Path
import sys, os
import json
from datetime import datetime

from uuid import uuid4

import qdarkstyle
from qdarkstyle.light.palette import LightPalette
from qdarkstyle.dark.palette import DarkPalette

###############################################################################

class Application(qtw.QApplication):
    
    def __init__(self, argv=[]):
        #{{{
        super().__init__(argv)
        self._argv = argv
        self._debug = ("--debug" in argv)
        self._force_reset = ("--reset" in argv)
        
        self.main_window = MainWindow(application=self)
        self.tab_widget = self.main_window.tab_widget
        
        self.startup()
        #}}}

    def startup(self):
        #{{{
        # Moved this code out of __init__ because I want to be able to 
        # "restart" the app without calling super().__init__ again.

        self.application_state_path = os.path.join(
                                config.active_profile.profile_dir, "shipping_conf.json")

        self._whoami = dm.WhoAmI()
        self.current_style = 'light'
        self.load_state()
        self.load_institutions()

        if self.application_state.setdefault('style', 'light') == 'light':
            self.setStyleSheet_light()
        elif self.application_state['style'] == 'dark':
            self.setStyleSheet_dark() 
        else:
            self.setStyleSheet_sisyphus()

        self.restore_tabs()
        #}}}

    def load_institutions(self):
        inst_data = dm.Institutions().data

        inst_sorted_by_name = sorted( [ (inst['name'], inst) for inst in inst_data ] )

        inst_by_id = { inst['id']: inst for _, inst in inst_sorted_by_name }

        country_list_unsorted = { x['country']['code']: x['country'] for x in inst_data }
        country_list_by_code = { x: country_list_unsorted[x] for x in sorted(country_list_unsorted.keys()) }


        for inst in inst_by_id.values():
            inst['country_code'] = inst['country']['code']
            del inst['country']
            country_list_by_code[inst['country_code']].setdefault('institution_ids', []).append(inst['id'])

        self.locations = {
            "countries": country_list_by_code,
            "institutions": inst_by_id,
        }

    @property
    def whoami(self):
        return self._whoami.data

    #{{{
    def setStyleSheet_light(self):
        light_stylesheet = qdarkstyle.load_stylesheet(palette=LightPalette)
        self.setStyleSheet(light_stylesheet)
        self.current_style = self.application_state['style'] = 'light'

    def setStyleSheet_dark(self):
        dark_stylesheet = qdarkstyle.load_stylesheet(palette=DarkPalette)
        self.setStyleSheet(dark_stylesheet)
        self.current_style = self.application_state['style'] = 'dark'

    def setStyleSheet_sisyphus(self):
        try:
            style_path = Sisyphus.get_path('resources/style.qss')
            self.setStyleSheet(Path(style_path).read_text())
        except FileNotFoundError as exc:
            msg = "Stylesheet not found."
            Style.error.print(msg)
            logger.error(msg)
        self.current_style = self.application_state['style'] = 'sisyphus'
    #}}}

    def reset_state(self):
        #{{{
        logger.warn("Resetting shipping application state") 
        self.application_state = {
            #"working_directory": os.path.normpath(os.path.expanduser('~/.sisyphus/shipping')),
            "current_tab": -1,
            "tabs": [],
            "workflows": {},
            "style": self.current_style,
        }
        self._force_reset = False
        #}}}

    def validate_state(self):
        #{{{
        if type(self.application_state.get('current_tab')) is not int:
            return False
        if type(self.application_state.get('tabs')) is not list:
            return False
        if type(self.application_state.get('workflows')) is not dict: 
            return False

        return True
        #}}}

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
                self.application_state = json.load(fp)
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
        #}}}

    def save_state(self):
        #{{{
        logger.debug("Saving application state")
        
        self.application_state['current_tab'] = self.tab_widget.currentIndex()

        with open(self.application_state_path, 'w') as fp:
            json.dump(self.application_state, fp, indent=4)
        #}}}

    def restore_tabs(self):
        #{{{
        logger.info(f"restoring tabs")
        while self.tab_widget.count():
            self.tab_widget.removeTab(0)
        
        curr_idx = self.application_state.get('current_tab', 0)

        for tab_index in range(len(self.application_state['tabs'])):
            self.restore_tab(tab_index=tab_index)

        if self.tab_widget.count() > 0:
            logger.info(f"setting current tab: {curr_idx}")
            self.tab_widget.setCurrentIndex(curr_idx)
        #}}}

    def restore_tab(self, *, tab_index=None):
        #{{{
        logger.info(f"restoring tab {tab_index}")
        if tab_index is None:
            raise ValueError("required parameter: tab_index")

        workflow_uuid = self.application_state['tabs'][tab_index]
        workflow_state = self.application_state['workflows'][workflow_uuid]

        restored_workflow = WorkflowWidget(application=self, uuid=workflow_uuid)
        logger.info(f"finished_init: {restored_workflow._finished_init}")
        self.tab_widget.addTab(restored_workflow, "uninitialized")
        restored_workflow.activate()
        #}}}        

    def create_new_tab(self, *, workflow_state=None):
        #{{{
        logger.info(f"{self.__class__.__name__}.create_new_tab()")
        new_uuid = uuid4().hex      
        if workflow_state is None:
            workflow_state = {
                'uuid': new_uuid,
                'current_page_id': "SelectPID",
            }
        elif workflow_state.get('uuid') is None:
            workflow_state['uuid'] = new_uuid

        self.application_state['workflows'][new_uuid] = workflow_state
        self.application_state['tabs'].append(new_uuid)

        new_workflow = WorkflowWidget(application=self, uuid=new_uuid)
        logger.info(f"finished_init: {new_workflow._finished_init}")
        self.tab_widget.addTab(new_workflow, "new workflow")
        new_workflow.update_tab_title()
        new_workflow.activate()

        idx = self.tab_widget.indexOf(new_workflow)
        self.tab_widget.setCurrentIndex(idx)
        #}}}

    def close_tab_by_obj(self, page_widget):
        index = self.tab_widget.indexOf(page_widget)
        self.close_tab_by_index(index)

    def close_tab_by_index(self, tab_index):
        #{{{
        # Either the user clicked the [X] on a tab, or they clicked
        # the 'Close' button.

        tab_content_widget = self.tab_widget.widget(tab_index)

        # Ask the tab_content_widget if it's okay to close. 
        if hasattr(tab_content_widget, "close_tab_requested"):
            retval = tab_content_widget.close_tab_requested()
            if not retval:
                return False

        if isinstance(tab_content_widget, WorkflowWidget):
            workflow_uuid = tab_content_widget.uuid
            self.application_state['tabs'].remove(workflow_uuid)
            del self.application_state['workflows'][workflow_uuid]

        tab_content_widget.deleteLater()
        self.tab_widget.removeTab(tab_index)

        return True
        #}}}

    def on_currentChanged(self, tab_index):
        self.application_state['current_tab'] = tab_index
        
    @property
    def working_directory(self):
        user_profile = config.active_profile.profile_data['users'].get(self.username, {})
        return user_profile.get('working_directory', config.active_profile.profile_dir)
        
    def update_status(self, message):
        self.main_window.status_bar.showMessage(message)

    @property
    def username(self):
        return self.whoami['username']

    @property
    def user_full_name(self):
        user_profile = config.active_profile.profile_data['users'].get(self.username, {})
        return user_profile.get('full_name', None) or self.whoami['full_name']
        
    @property
    def user_email(self):
        user_profile = config.active_profile.profile_data['users'].get(self.username, {})
        return user_profile.get('email', None) or self.whoami['email']

    def configure(self):
        #{{{
        self.save_state()
        current_profile = config.active_profile.profile_name

        dialog = ConfigDialog(self)
        dialog.exec()

        if config.active_profile.profile_name != current_profile:
            self.startup()
        #}}}

    def start_waiting(self):
        #{{{
        cw = self.tab_widget.currentWidget()
        if cw is not None:
            cpw = cw.current_page_widget
            if cpw is not None:
                cpw.start_waiting()
        self.processEvents()
        #}}}

    def stop_waiting(self):
        #{{{
        cw = self.tab_widget.currentWidget()
        if cw is not None:
            cpw = cw.current_page_widget
            if cpw is not None:
                cpw.stop_waiting()
        self.processEvents()
        #}}}
    
    def exit(self):
        #{{{
        logger.warning(f"{self.__class__.__name__}.exit(): quitting aplication")
        self.save_state()
        self.main_window.close()
        #}}}

    #{{{
    def debug_application_state(self):
        #Style.info.print(json.dumps(self.application_state, indent=4))
        from Sisyphus.Gui.Utilities.JSONViewer import QTreeView, JsonModel

        class JsonViewDialog(qtw.QDialog):
            def __init__(self, application_state):
                super().__init__()
                self.application_state = application_state
                self.setWindowTitle("Application State")
                self.main_layout = qtw.QVBoxLayout()
                self.main_layout.setContentsMargins(10, 10, 10, 10)
                self.setLayout(self.main_layout)

                self.treeview = QTreeView()
                self.jsonmodel = JsonModel()
                self.treeview.setModel(self.jsonmodel)
                self.jsonmodel.load(self.application_state)
                
                self.resize(800, 800)
                self.treeview.header().setSectionResizeMode(0, qtw.QHeaderView.ResizeMode.Stretch)
                self.treeview.setAlternatingRowColors(True)

                self.main_layout.addWidget(self.treeview)


        json_view_dialog = JsonViewDialog(self.application_state)
        json_view_dialog.exec()

    
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
    #}}}



