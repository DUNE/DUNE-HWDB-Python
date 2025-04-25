#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

HLD = highlight = "[bg=#999999,fg=#ffffff]"
HLI = highlight = "[bg=#009900,fg=#ffffff]"
HLW = highlight = "[bg=#999900,fg=#ffffff]"
HLE = highlight = "[bg=#990000,fg=#ffffff]" 

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

import os

from Sisyphus.Gui.Shipping.Screens import (
        SelectPID, SelectWorkflow,
        Packing1, PackingComplete,
        PreShipping1, PreShipping2, PreShipping3, PreShipping4a, PreShipping4b,
            PreShipping5, PreShipping6, PreShipping7, PreShippingComplete,
        Shipping1, Shipping2, Shipping3, Shipping4, Shipping5, 
            Shipping6, ShippingComplete,
        Transit1, TransitComplete,
        Receiving1, Receiving2, Receiving3, ReceivingComplete
)

###############################################################################

class WorkflowWidget(qtw.QWidget):
    def __init__(self, *, application=None, uuid=None):
        #{{{
        super().__init__()
        
        self._finished_init = False
        
        self.application = application
        if application is None:
            raise ValueError("required parameter: application")
        
        if uuid is None:
            raise ValueError("required parameter: uuid")
        self.uuid = uuid
        if uuid not in self.application.application_state['workflows']:
            raise ValueError("uuid not in workflows dict")
        

        logger.debug(f"{HLD}WorkflowWidget parent: {self.parent()}")

        self.create_page_stack()
        self._finished_init = True
        #}}}

    @property
    def application_state(self):
        return self.application.application_state

    @property
    def workflow_state(self):
        return self.application.application_state['workflows'][self.uuid]

    @property
    def current_page_id(self):
        return self.workflow_state['current_page_id']

    def set_current_page(self, new_page_id):
        
        if self.workflow_state['current_page_id'] != new_page_id:
            self.workflow_state['current_page_id'] = new_page_id
            self.activate()
        return new_page_id

    def activate(self):
        logger.debug(f"{HLD}{self.__class__.__name__}.activate()")
        self.page_stack.setCurrentWidget(self._page_lookup[self.current_page_id])
        self.update_tab_title()
        self.current_page_widget.activate()

    @property
    def current_page_widget(self):
        return self.page_stack.currentWidget()

    def save(self):
        self.application.save_state()

    def update_tab_title(self):
         logger.debug(f"{HLD}{self.__class__.__name__}.update_tab_title()")
         tab_index = self.application.tab_widget.indexOf(self)
         logger.debug(f"{HLD}(finished_init: {self._finished_init}, "
                    f" tab_index: {tab_index}, "
                    f" current_page_id: {self.current_page_widget.__class__.__name__}")
         self.application.tab_widget.setTabText(tab_index, self.current_page_widget.tab_title)

    def create_page_stack(self):
        #{{{
        self.page_stack = qtw.QStackedLayout(self)
        #self.page_stack = qtw.QVBoxLayout()

        logger.info("creating pages...")
        self._page_lookup = {
            "SelectPID": SelectPID(workflow=self),
            "SelectWorkflow": SelectWorkflow(workflow=self),

            "Packing1": Packing1(workflow=self),
            "PackingComplete": PackingComplete(workflow=self),

            "PreShipping1": PreShipping1(workflow=self),
            "PreShipping2": PreShipping2(workflow=self),
            "PreShipping3": PreShipping3(workflow=self),
            "PreShipping4a": PreShipping4a(workflow=self),
            "PreShipping4b": PreShipping4b(workflow=self),
            "PreShipping5": PreShipping5(workflow=self),
            "PreShipping6": PreShipping6(workflow=self),
            "PreShipping7": PreShipping7(workflow=self),
            "PreShippingComplete": PreShippingComplete(workflow=self),

            "Shipping1": Shipping1(workflow=self),
            "Shipping2": Shipping2(workflow=self),
            "Shipping3": Shipping3(workflow=self),
            "Shipping4": Shipping4(workflow=self),
            "Shipping5": Shipping5(workflow=self),
            "Shipping6": Shipping6(workflow=self),
            "ShippingComplete": ShippingComplete(workflow=self),

            "Transit1": Transit1(workflow=self),
            "TransitComplete": TransitComplete(workflow=self),

            "Receiving1": Receiving1(workflow=self),
            "Receiving2": Receiving2(workflow=self),
            "Receiving3": Receiving3(workflow=self),
            "ReceivingComplete": ReceivingComplete(workflow=self),
        }
        logger.info("...finished creating pages")

        for page_id, page in self._page_lookup.items():
            self.page_stack.addWidget(page)

        self._next_page = {
            "SelectPID": "SelectWorkflow",
            "SelectWorkflow": None, # handle special

            "Packing1": "PackingComplete",
            "PackingComplete": None,

            "PreShipping1": "PreShipping2",
            "PreShipping2": "PreShipping3",
            "PreShipping3": "PreShipping4a",
            "PreShipping4a": "PreShipping4b",
            "PreShipping4b": "PreShipping5",
            "PreShipping5": "PreShipping6",
            "PreShipping6": "PreShipping7",
            "PreShipping7": "PreShippingComplete",
            "PreShippingComplete": "Shipping1",

            "Shipping1": "Shipping2",
            "Shipping2": "Shipping3",
            "Shipping3": "Shipping4",
            "Shipping3": "Shipping4",
            "Shipping4": "Shipping5",
            "Shipping5": "Shipping6",
            "Shipping6": "ShippingComplete",
            "ShippingComplete": None,

            "Transit1": "TransitComplete",
            "TransitComplete": None,

            "Receiving1": "Receiving2",
            "Receiving2": "Receiving3",
            "Receiving3": "ReceivingComplete",
            "ReceivingComplete": None,
        }

        self._prev_page = {
            "SelectPID": None,
            "SelectWorkflow": "SelectPID",

            "Packing1": "SelectWorkflow",
            "PackingComplete": None,

            "PreShipping1": "SelectWorkflow",
            "PreShipping2": "PreShipping1",
            "PreShipping3": "PreShipping2",
            "PreShipping4a": "PreShipping3",
            "PreShipping4b": "PreShipping4a",
            "PreShipping5": "PreShipping4b",
            "PreShipping6": "PreShipping5",
            "PreShipping7": "PreShipping6",
            #"PreShippingComplete": "PreShipping7
            "PreShippingComplete": None,
            
            "Shipping1": "SelectWorkflow",
            "Shipping2": "Shipping1",
            "Shipping3": "Shipping2",
            "Shipping4": "Shipping3",
            "Shipping5": "Shipping4",
            "Shipping6": "Shipping5",
            #"ShippingComplete": None,
            "ShippingComplete": "Shipping6",

            "Transit1": "SelectWorkflow",
            "TransitComplete": None,

            "Receiving1": "SelectWorkflow",
            "Receiving2": "Receiving1",
            "Receiving3": "Receiving2",
            "ReceivingComplete": None,
        }

        #self.test_widget = qtw.QLabel("Test Widget")
        #self.test_layout = qtw.QVBoxLayout()
        #self.test_layout.addWidget(self.test_widget)

        #self.setLayout(self.test_layout)

        self.setLayout(self.page_stack)
        #}}}

    def navigate_next(self):
        #{{{
        ok = self.current_page_widget.on_navigate_next()

        if not ok:
            logger.warning(f"{self.current_page_id} rejected 'on_navigate_next'")
            return

        next_page_id = self._next_page[self.current_page_id]
        logger.debug(f"navigate_next: {self.current_page_id} -> {next_page_id}")
        if next_page_id is not None:
            self.set_current_page(next_page_id)
            return

        logger.debug("special handling code")
        if self.current_page_id == 'SelectWorkflow':
            page_state = self.workflow_state.setdefault('SelectWorkflow', {})
            if page_state['workflow_type'] == "packing":
                next_page_id = "Packing1"
            elif page_state['workflow_type'] == "preshipping":
                next_page_id = "PreShipping1"
            elif page_state['workflow_type'] == "shipping":
                next_page_id = "Shipping1"
            elif page_state['workflow_type'] == "transit":
                next_page_id = "Transit1"
            elif page_state['workflow_type'] == "receiving":
                next_page_id = "Receiving1"
            else:
                logger.warning(f"unrecognized workflow type {self.workflow_type}")
                next_page_id = "SelectWorkflow"

            self.set_current_page(next_page_id)
        #}}}

    def navigate_prev(self):
        ok = self.current_page_widget.on_navigate_prev()
        
        if not ok:
            return

        prev_page_id = self._prev_page[self.current_page_id]
        if prev_page_id is not None:
            self.set_current_page(prev_page_id)
            return

    @property
    def part_id(self):
        return self.workflow_state.get('part_info', {}).get('part_id', None)

    @property
    def working_directory(self):
        if self.part_id is None:
            retval = self.application.working_directory
        else:
            retval = os.path.normpath(
                    os.path.join(self.application.working_directory, self.part_id))
        os.makedirs(retval, exist_ok=True)
        return retval


    def close_tab_requested(self):
        # The application is asking to close this tab. Return True if it's okay
        # to close it, otherwise return False
        # Delegate this to the page that's currently showing.
        return self.current_page_widget.close_tab_requested()

    def get_page_by_id(self, page_id):
        return self._page_lookup.get(page_id, None) 


    #}}}




































