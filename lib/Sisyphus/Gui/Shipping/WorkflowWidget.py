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
        PreShipping1, PreShipping2a, PreShipping2b, PreShipping3a, PreShipping3b,
            PreShipping4, PreShipping5, PreShipping6, PreShippingComplete,
        Shipping1, Shipping2, Shipping3, Shipping4, Shipping5, 
            Shipping6, ShippingComplete,
        Transit1, TransitComplete,
        Receiving1, Receiving2, Receiving3, ReceivingComplete
)

###############################################################################

class WorkflowWidget(qtw.QWidget):
    def __init__(self, *, owner=None, uuid=None):
        #{{{
        self._finished_init = False
        if owner is None:
            raise ValueError("required parameter: owner")
        self.application = self.owner = owner
        
        if uuid is None:
            raise ValueError("required parameter: uuid")
        self.uuid = uuid
        if uuid not in self.application.app_state['workflows']:
            raise ValueError("uuid not in workflows dict")
        
        super().__init__()

        logger.debug(f"{HLD}WorkflowWidget parent: {self.parent()}")

        self.create_page_stack()
        self._finished_init = True
        #}}}

    @property
    def app_state(self):
        return self.application.app_state

    @property
    def workflow_state(self):
        return self.application.app_state['workflows'][self.uuid]

    @property
    def current_page_id(self):
        return self.workflow_state['current_page_id']

    def set_current_page(self, new_page_id):
        
        if self.workflow_state['current_page_id'] != new_page_id:
            self.workflow_state['current_page_id'] = new_page_id
            self.activate()
            #current_page_widget = self._page_lookup[page_id]
            #self.page_stack.setCurrentWidget(current_page_widget)
            #current_page_widget.restore()
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

    #def restore(self):
    #    self.page_stack.currentWidget().restore()

    #def update_tab_title(self, title):
    #    logger.info(f"{HLI}{self.__class__.__name__}.update_tab_title")
    #    self.title = title
    #    idx = self.application.tab_widget.indexOf(self)
    #    self.application.tab_widget.setTabText(idx, title)

    def update_tab_title(self):
         logger.debug(f"{HLD}{self.__class__.__name__}.update_tab_title()")
         tab_index = self.application.tab_widget.indexOf(self)
         logger.debug(f"{HLD}(finished_init: {self._finished_init}, "
                    f" tab_index: {tab_index}, "
                    f" current_page_id: {self.current_page_widget.__class__.__name__}")
         #self.application.tab_widget.setTabText(tab_index, self.current_page_widget.page_short_name)
         self.application.tab_widget.setTabText(tab_index, self.current_page_widget.tab_title)


    def create_page_stack(self):
        #{{{
        self.page_stack = qtw.QStackedLayout(self)
        #self.page_stack = qtw.QVBoxLayout()

        logger.info("creating pages...")
        self._page_lookup = {
            "SelectPID": SelectPID(owner=self),
            "SelectWorkflow": SelectWorkflow(owner=self),

            "Packing1": Packing1(owner=self),
            "PackingComplete": PackingComplete(owner=self),

            "PreShipping1": PreShipping1(owner=self),
            "PreShipping2a": PreShipping2a(owner=self),
            "PreShipping2b": PreShipping2b(owner=self),
            "PreShipping3a": PreShipping3a(owner=self),
            "PreShipping3b": PreShipping3b(owner=self),
            "PreShipping4": PreShipping4(owner=self),
            "PreShipping5": PreShipping5(owner=self),
            "PreShipping6": PreShipping6(owner=self),
            "PreShippingComplete": PreShippingComplete(owner=self),

            "Shipping1": Shipping1(owner=self),
            "Shipping2": Shipping2(owner=self),
            "Shipping3": Shipping3(owner=self),
            "Shipping4": Shipping4(owner=self),
            "Shipping5": Shipping5(owner=self),
            "Shipping6": Shipping6(owner=self),
            "ShippingComplete": ShippingComplete(owner=self),

            "Transit1": Transit1(owner=self),
            "TransitComplete": TransitComplete(owner=self),

            "Receiving1": Receiving1(owner=self),
            "Receiving2": Receiving2(owner=self),
            "Receiving3": Receiving3(owner=self),
            "ReceivingComplete": ReceivingComplete(owner=self),
        }
        logger.info("...finished creating pages")

        for page_id, page in self._page_lookup.items():
            self.page_stack.addWidget(page)

        self._next_page = {
            "SelectPID": "SelectWorkflow",
            "SelectWorkflow": None, # handle special

            "Packing1": "PackingComplete",
            "PackingComplete": None,

            "PreShipping1": "PreShipping2a",
            "PreShipping2a": "PreShipping2b",
            "PreShipping2b": "PreShipping3a",
            "PreShipping3a": "PreShipping3b",
            "PreShipping3b": "PreShipping4",
            "PreShipping4": "PreShipping5",
            "PreShipping5": "PreShipping6",
            "PreShipping6": "PreShippingComplete",
            "PreShippingComplete": None,

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
            "PreShipping2a": "PreShipping1",
            "PreShipping2b": "PreShipping2a",
            "PreShipping3a": "PreShipping2",
            "PreShipping3b": "PreShipping3a",
            "PreShipping4": "PreShipping3b",
            "PreShipping5": "PreShipping4",
            "PreShipping6": "PreShipping5",
            "PreShippingComplete": None,
            #"PreShippingComplete": "PreShipping6",

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
            #self.set_page(prev_page)
            self.set_current_page(prev_page_id)
            return
        #print("special handling code")

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


    #}}}




































