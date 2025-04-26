#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)
#logger.setLevel("INFO")

from Sisyphus.Gui import DataModel as dm
from Sisyphus.Utils.Terminal.Style import Style
from . import widgets as zw
from .LinkedWidget import LinkedWidget
import json
import os
from copy import copy
import time

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtGui as qtg

###############################################################################

STYLE_LARGE_BUTTON = """
    font-size: 12pt;
    padding: 5px 15px;
"""

STYLE_SMALL_BUTTON = """
    padding: 5px 15px;
"""

class PageWidget(qtw.QWidget):
    #{{{

    # Override this on pages where a workflow is complete and there's no
    # sense in asking the user if they are sure before closing.
    _warn_before_closing = True

    def __init__(self, *args, **kwargs):
        self.workflow = kwargs.pop("workflow", None)
        if self.workflow is None:
            raise ValueError("required paramter: workflow")

        self.application = self.workflow.application

        super().__init__(*args, **kwargs)
        self._application_state = self.workflow.application_state
        self._workflow_state = self.workflow.workflow_state
        self.page_id = self.__class__.__name__.split('.')[-1]

        self.title_bar = TitleBar(page=self)
        self.nav_bar = NavBar(page=self)

        # Make the PageWidget's layout be a stacked layout that contains
        # the "real" widget containing the actual page contents, and
        # a hidden overlay that only shows up when the application is 
        # waiting for something from the database.
        self.master_layout = qtw.QStackedLayout()
        self.master_layout.setStackingMode(qtw.QStackedLayout.StackAll)
        super().setLayout(self.master_layout)
        self.main_widget = qtw.QWidget()
        self.overlay = WaitOverlay()
        self.master_layout.addWidget(self.overlay)
        self.master_layout.addWidget(self.main_widget)
        self.master_layout.setCurrentWidget(self.main_widget)
        self._wait_count = 0

    def setLayout(self, layout):
        # Re-interpret "setLayout" to mean for the main_widget instead
        # of for the entire PageWidget.
        self.main_widget.setLayout(layout)

    def wait(self):
        # Returns a very simple context manager that shows and
        # hides the overlay. It's better to use this than to use
        # the "start_waiting" and "stop_waiting" methods because
        # the context manager guarantees that the overlay will be
        # hidden when the task is finished, even if an exception
        # is raised.
        page = self
        class wait_mgr:
            def __enter__(self):
                page._wait_count += 1
                page.start_waiting()
            def __exit__(self, type, value, traceback):
                page._wait_count -= 1
                if page._wait_count <= 0:
                    page.stop_waiting()
        return wait_mgr()
                

    def start_waiting(self):
        # Show the overlay
        self.master_layout.setCurrentWidget(self.overlay)
        self.application.processEvents()
    
    def stop_waiting(self):
        # Hide the overlay
        self.master_layout.setCurrentWidget(self.main_widget)
        self.application.processEvents()
    


    @property
    def page_name(self):
        try:
            return self._page_name
        except AttributeError:
            logger.warning(f"{self.__class__.__name__} page_name not set!")
            self._page_name = self.page_id
            return self._page_name

    @page_name.setter
    def page_name(self, value):
        self._page_name = value

    @property
    def page_short_name(self):
        try:
            return self._page_short_name
        except AttributeError:
            logger.warning("page_short_name not set!")
            self._page_short_name = self.page_name
            return self._page_short_name

    @property
    def part_id(self):
        return self.workflow_state.get("part_info", {}).get("part_id", None)

    @property
    def application_state(self):
        return self.workflow.application_state

    @property
    def workflow_state(self):
        return self.workflow.workflow_state

    @workflow_state.setter
    def workflow_state(self, value):
        self.workflow.workflow_state = value
        return value

    @property
    def page_state(self):
        return self.workflow.workflow_state.setdefault(self.page_id, {})

    def save(self):
        logger.debug(f"{self.__class__.__name__}.save()")
        self.workflow.save()

    @property
    def tab_title(self):
        if self.part_id is not None:
            tab_title = f"{self.part_id}\n{self.page_short_name}"
        else:
            tab_title = f"{self.page_short_name}"
        return tab_title

    def activate(self):
        # call when switching to this page
        logger.info(f"{self.__class__.__name__}.activate()")
        logger.info(f"(workflow init: {self.workflow._finished_init})")
        self.restore()
        #self.refresh()
        self.application.update_status(self.page_name)

    def restore(self):
        for linked_widget in self.findChildren(LinkedWidget):
            linked_widget.restore()

    def refresh(self):
        # overload this method to add an action when the content of the page
        # has changed, e.g., to enable/disable nav buttons
        logger.info(f"{self.__class__.__name__}.refresh()")
        self.title_bar.page_subtitle.restore()

    def on_navigate_next(self):
        self.save()
        return True

    def on_navigate_prev(self):
        self.save()
        return True


    def close_tab_requested(self):
        # The user is trying to close this tab. Ask them if they are sure.
        # Return True if it's okay to close, or False if they changed their mind.

        logger.error(f"close_tab_requested, _warn_berfore_closing: {self._warn_before_closing}")
        logger.error(f"my class is: {self.__class__.__name__}")
        if self.__class__._warn_before_closing:
 
            retval = qtw.QMessageBox.warning(
                        self.application.main_window,
                        "Warning",
                        "If you remove this workflow, you will not be able to return to it. "
                                "Are you sure you want to remove this workflow?",
                        qtw.QMessageBox.Ok | qtw.QMessageBox.Cancel)

            confirm_remove_tab = retval == qtw.QMessageBox.Ok

            if confirm_remove_tab:
                logger.info("The user elected to close this tab.")
            else:
                logger.info("The user decided to keep the tab.")
        else:
            logger.info("This tab will close. No confirmation required.")
            confirm_remove_tab = True

        return confirm_remove_tab

    #}}}

class WaitOverlay(qtw.QWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.vertical_layout = qtw.QVBoxLayout()
        self.horizontal_layout = qtw.QHBoxLayout()

        self.overlay_widget = qtw.QLabel("Please Wait...")
        self.overlay_widget.setStyleSheet(
                "font-size: 20pt; "
                "background-color: rgba(0, 0, 0, 64); ")
        self.overlay_widget.setAlignment(qtc.Qt.AlignCenter)
        self.overlay_widget.setMinimumSize(qtc.QSize(400, 300))
        
        self.horizontal_layout.addStretch()
        self.horizontal_layout.addWidget(self.overlay_widget)
        self.horizontal_layout.addStretch()

        self.vertical_layout.addStretch()
        self.vertical_layout.addLayout(self.horizontal_layout)
        self.vertical_layout.addStretch()

        self.setLayout(self.vertical_layout)
    #}}}


class TitleBar(qtw.QWidget):
    #{{{
    def __init__(self, *args, **kwargs):

        self.page = kwargs.pop('page', None)        
        if self.page is None:
            raise ValueError("required parameter: page")

        super().__init__(*args, **kwargs)
        
        main_layout = qtw.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.page_title = qtw.QLabel(self.page.page_name)
        self.page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        self.page_title.setAlignment(qtc.Qt.AlignCenter)

        main_layout.addWidget(self.page_title)

        self.page_subtitle = zw.ZLabel(
                        page=self.page, 
                        key='subtitle', 
                        source='attr:part_id',
                        default='[no part_id yet]')
        self.page_subtitle.setAlignment(qtc.Qt.AlignCenter)
        
        main_layout.addWidget(self.page_subtitle)

        self.setLayout(main_layout)
    #}}}

class NavBar(qtw.QWidget):
    #{{{
    def __init__(self, *args, **kwargs):

        self.page = kwargs.pop('page', None)
        if self.page is None:
            raise ValueError("required parameter: page")
        self.workflow = self.page.workflow
        self.application = self.page.application

        super().__init__(*args, **kwargs)

        main_layout = qtw.QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.back_button = qtw.QPushButton("Back")
        self.back_button.setStyleSheet(STYLE_LARGE_BUTTON)
        self.back_button.clicked.connect(self.page.workflow.navigate_prev)

        self.continue_button = qtw.QPushButton("Continue")
        self.continue_button.setStyleSheet(STYLE_LARGE_BUTTON)
        self.continue_button.clicked.connect(self.page.workflow.navigate_next)

        self.close_tab_button = qtw.QPushButton("Close Tab")
        self.close_tab_button.setStyleSheet(STYLE_LARGE_BUTTON)
        #self.close_tab_button.clicked.connect(self.application.close_tab)
        self.close_tab_button.clicked.connect(
                        lambda: self.application.close_tab_by_obj(self.workflow))

        main_layout.addWidget(self.back_button)
        main_layout.addStretch()
        main_layout.addWidget(self.close_tab_button)
        main_layout.addWidget(self.continue_button)
        self.close_tab_button.setVisible(False)


        self.setLayout(main_layout)

    def set_buttons(self, button_list):
        button_list = copy(button_list)

        if 'back' in button_list:
            self.back_button.setVisible(True)
        else:
            self.back_button.setVisible(False)

        if 'continue' in button_list:
            self.continue_button.setVisible(True)
        else:
            self.continue_button.setVisible(False)

        if 'close' in button_list:
            self.close_tab_button.setVisible(True)
        else:
            self.close_tab_button.setVisible(False)


    #}}}

