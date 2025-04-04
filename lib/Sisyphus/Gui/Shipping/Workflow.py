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


from copy import deepcopy
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
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtGui import QIcon

from Sisyphus.Gui.Shipping.Screens import (
        SelectPID, SelectWorkflow,
        Packing1, PackingComplete,
        PreShipping1, PreShipping2, PreShipping3a, PreShipping3b, PreShipping4,
            PreShipping5, PreShipping6, PreShippingComplete,
        Shipping1, Shipping2, Shipping3, Shipping4, Shipping5, 
            Shipping6, ShippingComplete,
        Transit1, TransitComplete,
        Receiving1, Receiving2, Receiving3, ReceivingComplete
)

NEW_TAB_STATE = {
    "current_page": "SelectPID",
    #"SelectWorkflow": {"workflow_type": "preshipping"}
}
#}}}

class Workflow(QWidget):
    #{{{
    def __init__(self, app, app_state, tab_state=None):
        super().__init__()

        self.app = app
        self.app_state = app_state
        self.tab_state = tab_state or deepcopy(NEW_TAB_STATE)

        self.create_page_stack()
        self.current_page = None

        self.restore()

    def save(self):
        self.app.save_state()

    def restore(self):
        state = self.tab_state

        # self.title = state['title']
        self.set_page(state.get('current_page', 'SelectPID'))


    def update_title(self, title):
        self.title = title
        idx = self.app.tab_widget.indexOf(self)
        self.app.tab_widget.setTabText(idx, title)

    def create_page_stack(self):
        #{{{
        self.page_stack = QStackedLayout(self)

        logger.info("creating pages...")
        self.page_lookup = {
            "SelectPID": SelectPID(self),
            "SelectWorkflow": SelectWorkflow(self),

            "Packing1": Packing1(self),
            "PackingComplete": PackingComplete(self),

            "PreShipping1": PreShipping1(self),
            "PreShipping2": PreShipping2(self),
            "PreShipping3a": PreShipping3a(self),
            "PreShipping3b": PreShipping3b(self),
            "PreShipping4": PreShipping4(self),
            "PreShipping5": PreShipping5(self),
            "PreShipping6": PreShipping6(self),
            "PreShippingComplete": PreShippingComplete(self),

            "Shipping1": Shipping1(self),
            "Shipping2": Shipping2(self),
            "Shipping3": Shipping3(self),
            "Shipping4": Shipping4(self),
            "Shipping5": Shipping5(self),
            "Shipping6": Shipping6(self),
            "ShippingComplete": ShippingComplete(self),

            "Transit1": Transit1(self),
            "TransitComplete": TransitComplete(self),

            "Receiving1": Receiving1(self),
            "Receiving2": Receiving2(self),
            "Receiving3": Receiving3(self),
            "ReceivingComplete": ReceivingComplete(self),
        }
        logger.info("...finished creating pages")

        for page_id, page in self.page_lookup.items():
            self.page_stack.addWidget(page)

        self.next_page = {
            "SelectPID": "SelectWorkflow",
            "SelectWorkflow": None, # handle special

            "Packing1": "PackingComplete",
            "PackingComplete": None,

            "PreShipping1": "PreShipping2",
            "PreShipping2": "PreShipping3a",
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
            "ShippingComplete": None,

            "Transit1": "TransitComplete",
            "TransitComplete": None,

            "Receiving1": "Receiving2",
            "Receiving2": "Receiving3",
            "Receiving3": "ReceivingComplete",
            "ReceivingComplete": None,
        }

        self.prev_page = {
            "SelectPID": None,
            "SelectWorkflow": "SelectPID",

            "Packing1": "SelectWorkflow",
            "PackingComplete": None,

            "PreShipping1": "SelectWorkflow",
            "PreShipping2": "PreShipping1",
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

        self.setLayout(self.page_stack)
        #}}}

    def set_page(self, page_id, state=None):
        state = state or {}

        self.current_page = page_id
        self.tab_state['current_page'] = page_id

        self.page_stack.setCurrentWidget(self.page_lookup[page_id])

        self.page_lookup[page_id].restore()
        logger.debug(f"current page set to: {self.current_page}")

    def navigate_next(self):
        self.page_lookup[self.current_page].on_navigate_next()

        next_page = self.next_page[self.current_page]
        logger.debug(f"navigate_next: {self.current_page} -> {next_page}")
        if next_page is not None:
            self.set_page(next_page)
            return

        logger.debug("special handling code")
        if self.current_page == 'SelectWorkflow':
            page_state = self.tab_state.setdefault('SelectWorkflow', {})
            if page_state['workflow_type'] == "packing":
                next_page = "Packing1"
            elif page_state['workflow_type'] == "preshipping":
                next_page = "PreShipping1"
            elif page_state['workflow_type'] == "shipping":
                next_page = "Shipping1"
            elif page_state['workflow_type'] == "transit":
                next_page = "Transit1"
            elif page_state['workflow_type'] == "receiving":
                next_page = "Receiving1"
            else:
                logger.warning(f"unrecognized workflow type {self.workflow_type}")
                next_page = "SelectWorkflow"

            self.set_page(next_page)

    def navigate_prev(self):
        self.page_lookup[self.current_page].on_navigate_prev()
        
        prev_page = self.prev_page[self.current_page]
        if prev_page is not None:
            self.set_page(prev_page)
            return
        #print("special handling code")
    #}}}




































