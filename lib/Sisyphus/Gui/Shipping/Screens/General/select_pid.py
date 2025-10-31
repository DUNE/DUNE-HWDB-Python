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
from Sisyphus.Gui.Shipping.Widgets.PageWidget import PageWidget
from Sisyphus.Gui.Shipping import Widgets as zw
from Sisyphus.Gui.Shipping.Tasks import Database as dbt

from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc

import concurrent.futures
import threading

NUM_THREADS = 50
_executor = concurrent.futures.ThreadPoolExecutor(
                    max_workers=NUM_THREADS,
                    thread_name_prefix='select_pid_UI')


###############################################################################

class SelectPID(PageWidget):
    page_name = "Select PID"
    page_short_name = "Select PID"

    def __init__(self, *args, **kwargs):
        #{{{
        super().__init__(*args, **kwargs)
        
        default_result_msg = "<i>(Enter a PID and click 'find')</i>"

        self.pid_text_box = zw.ZLineEdit(page=self, key='search_part_id')

        self.completer = qtw.QCompleter(sorted(self.application_state.setdefault('recent_searches', [])))
        self.pid_text_box.setCompleter(self.completer)
        self.find_button = qtw.QPushButton("find")


        self.part_details = zw.ZPartDetails(
                                    page=self, 
                                    key='part_details',
                                    source='workflow:part_info')
        self.part_details.setMinimumSize(600, 400)

        self.find_button.setStyleSheet(zw.STYLE_SMALL_BUTTON)
        self.find_button.clicked.connect(self.lookup_pid)
        

        # ----------------------------------------------------------------------
        # Create checkboxes
        # ----------------------------------------------------------------------
        msg = "Shipping to SURF: Shipping directly to the SD warehouse/SURF."
        self.confirm_surf_checkbox = zw.ZCheckBox(page=self, text=msg, key="confirm_surf")
        
        msg = "Shipping to non-SURF: Shipping to a place that is not warehouse/SURF."
        self.confirm_non_surf_checkbox = zw.ZCheckBox(page=self, text=msg, key="confirm_non_surf")

        msg = ("Transshipping to SURF: Shipping to an intermediate non-SURF location.\n"
              "Then without opening the shipping box, it will be sent to SURF sometime in the future.")
        self.confirm_transshipping_checkbox = zw.ZCheckBox(page=self, text=msg, key="confirm_transshipping")
        # ----------------------------------------------------------------------
        # Restore from workflow_state if available
        # ----------------------------------------------------------------------
        select_pid_state = self.workflow_state.get("SelectPID", {})
        surf_state  = select_pid_state.get("confirm_surf")
        non_state   = select_pid_state.get("confirm_non_surf")
        trans_state = select_pid_state.get("confirm_transshipping")
        if any(v is True or v is False for v in (surf_state, non_state, trans_state)):
            # At least one saved value exists — use stored states
            self.confirm_surf_checkbox.setChecked(bool(surf_state))
            self.confirm_non_surf_checkbox.setChecked(bool(non_state))
            self.confirm_transshipping_checkbox.setChecked(bool(trans_state))
        else:
            # No saved values yet — use defaults
            self.confirm_surf_checkbox.setChecked(True)
            self.confirm_non_surf_checkbox.setChecked(False)
            self.confirm_transshipping_checkbox.setChecked(False)
    


        
        # Now that states are clean, build the layout
        self._setup_UI()

        # --- Connect exclusivity enforcement AFTER layout creation ---
        for cb in (
                self.confirm_surf_checkbox,
                self.confirm_non_surf_checkbox,
                self.confirm_transshipping_checkbox,
        ):
            cb.stateChanged.connect(self._enforce_single_checkbox)

       
        
        #self._setup_UI()

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
        # The shipping route selection
        
        #affirm_layout = qtw.QHBoxLayout()
        #affirm_layout.addSpacing(10)

        surf_layout = qtw.QVBoxLayout()
        surf_layout.addWidget(self.confirm_surf_checkbox)
        surf_layout.setContentsMargins(0, 0, 0, 0)
        surf_layout.setSpacing(0)
        surf_widget = qtw.QWidget()
        surf_widget.setLayout(surf_layout)

        nonsurf_layout = qtw.QVBoxLayout()
        nonsurf_layout.addWidget(self.confirm_non_surf_checkbox)
        nonsurf_layout.setContentsMargins(0, 0, 0, 0)
        nonsurf_layout.setSpacing(0)
        nonsurf_widget = qtw.QWidget()
        nonsurf_widget.setLayout(nonsurf_layout)

        transshipping_layout = qtw.QVBoxLayout()
        transshipping_layout.addWidget(self.confirm_transshipping_checkbox)
        transshipping_layout.setContentsMargins(0, 0, 0, 0)
        transshipping_layout.setSpacing(0)
        transshipping_widget = qtw.QWidget()
        transshipping_widget.setLayout(transshipping_layout)
        
        #affirm_layout.addWidget(surf_widget)
        #affirm_widget = qtw.QWidget()
        #affirm_widget.setLayout(affirm_layout)
        #main_layout.addWidget(affirm_widget)
        main_layout.addWidget(surf_widget)
        main_layout.addWidget(nonsurf_widget)
        main_layout.addWidget(transshipping_widget)
        main_layout.addSpacing(10)
        ############

        main_layout.addWidget(self.part_details)


        main_layout.addStretch()
        main_layout.addWidget(self.nav_bar)
        self.nav_bar.set_buttons(['continue'])

        self.setLayout(main_layout)

        #}}}

    def _enforce_single_checkbox(self, state):
        """Ensure only one checkbox can be checked at a time."""
        if getattr(self, "_enforcing", False):
            return
    
        sender = self.sender()

        if state:  # only run when something is checked
            self._enforcing = True  # start guard
            for cb in (
                    self.confirm_surf_checkbox,
                    self.confirm_non_surf_checkbox,
                    self.confirm_transshipping_checkbox,
            ):
                if cb is not sender:
                    cb.setChecked(False)  # allow signal to fire normally
            self._enforcing = False  # end guard
        
        '''
        if state:  # only react when something was checked
            for cb in (
                self.confirm_surf_checkbox,
                self.confirm_non_surf_checkbox,
                self.confirm_transshipping_checkbox,
            ):
                if cb is not sender:
                    cb.blockSignals(True)
                    cb.setChecked(False)
                    cb.blockSignals(False)
        else:
            # if user tries to uncheck the only one, re-check it
            if not any(cb.isChecked() for cb in (
                self.confirm_surf_checkbox,
                self.confirm_non_surf_checkbox,
                self.confirm_transshipping_checkbox,
            )):
                sender.blockSignals(True)
                sender.setChecked(True)
                sender.blockSignals(False)
        '''
        
    def lookup_pid(self):
        #{{{

        part_id = self.page_state['search_part_id'] or ""

        with self.wait():
            wfst = _executor.submit(
                            dbt.download_part_info,
                            part_id,
                            refresh=True, # don't use the cache
                            status_callback=self.application.update_status)

            #workflow_state = dbt.download_part_info(
            #                        part_id,
            #                        refresh=True, # don't use the cache
            #                        status_callback=self.application.update_status)
            workflow_state = wfst.result()

        # If the part was not found, download_part_info will return a dict
        # with the part_info and all the screen info blanked out, so it's
        # still okay to update workflow_state with it, whether the part was
        # found or not
        self.workflow_state.update(workflow_state)

        if not self.part_id:
            qtw.QMessageBox.warning(
                            self.application.main_window, 
                            "Not Found", 
                            f"{part_id} was not found.",
                            qtw.QMessageBox.Ok)
        else:
            self.append_recent_search(self.part_id)

        self.restore() # update dynamic widgets with new data
        self.refresh() # update navigation bar
 
        #}}}
    
    def append_recent_search(self, part_id):
        #{{{
        rs = self.application_state['recent_searches']

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


        # Explicitly read and normalize checkbox states
        surf = self.confirm_surf_checkbox.isChecked()
        non_surf = self.confirm_non_surf_checkbox.isChecked()
        trans = self.confirm_transshipping_checkbox.isChecked()
        # Force exclusivity truth logic at save time
        self.workflow_state['confirm_surf'] = surf and not (non_surf or trans)
        self.workflow_state['confirm_non_surf'] = non_surf and not (surf or trans)
        self.workflow_state['confirm_transshipping'] = trans and not (surf or non_surf)
    
        '''
        self.workflow_state['user_name'] = self.name_text_box.text().strip()
        self.workflow_state['user_email'] = self.email_text_box.text().strip()

        if self.workflow_state['user_name'] != "":
            self.application_state['default_name'] = self.workflow_state['user_name']

        if self.workflow_state['user_email'] != "":
            self.application_state['default_email'] = self.workflow_state['user_email']
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




