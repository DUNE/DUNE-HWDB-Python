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
import json

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

#from PyQt5.QtCore import QSize, Qt, pyqtSignal, pyqtSlot, QDateTime

'''
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
    QButtonGroup,
    QDateTimeEdit,
    QFileDialog,
)
'''

class PageWidget(qtw.QWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        super().__init__(*args, **kwargs)
        self.workflow = self.parent()
        self._app_state = self.workflow.app_state
        self._tab_state = self.workflow.tab_state
        self.page_id = self.__class__.__name__.split('.')[-1]

        # Use page_id as the default name, but should be 
        # overridden if you want a nicer human-readable name
        self.page_name = self.page_id

        self.nav_bar = NavBar(workflow = self.workflow)


    @property
    def app_state(self):
        return self.workflow.app_state

    @property
    def tab_state(self):
        return self.workflow.tab_state
    @tab_state.setter
    def tab_state(self, value):
        self.workflow.tab_state = value
        return value

    @property
    def page_state(self):
        return self.workflow.tab_state.setdefault(self.page_id, {})

    def save(self):
        logger.debug(f"{self.__class__.__name__}.save()")

    def restore(self):
        logger.debug(f"{self.__class__.__name__}.restore()")

        part_id = self.tab_state.get("part_info", {}).get("part_id", None)
        if part_id is not None:
            self.workflow.update_title(f"{part_id}\n{self.page_name}")
        else:
            self.workflow.update_title(f"{self.page_name}")

        for linked_widget in self.findChildren(LinkedWidget):
            linked_widget.restore()


        self.update()

    def update(self):
        # overload this method to add an action when the content of the page
        # has changed, e.g., to enable/disable nav buttons
        logger.debug(f"{self.__class__.__name__}.update()")


    def on_navigate_next(self):
        logger.debug(f"{self.__class__.__name__}.on_navigate_next()")
        ...

    def on_navigate_prev(self):
        logger.debug(f"{self.__class__.__name__}.on_navigate_prev()")
        ...
    #}}}

class NavBar(qtw.QWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")

        self.workflow = kwargs.pop('workflow', None)
        if self.workflow is None:
            raise ValueError("required parameter: workflow")

        super().__init__(*args, **kwargs)

        nav_layout = qtw.QHBoxLayout()

        self.back_button = qtw.QPushButton("Back")
        self.back_button.clicked.connect(self.workflow.navigate_prev)

        self.continue_button = qtw.QPushButton("Continue")
        self.continue_button.clicked.connect(self.workflow.navigate_next)

        nav_layout.addWidget(self.back_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.continue_button)

        self.setLayout(nav_layout)
    #}}}

class LinkedWidget:
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"LinkedWidget.__init__(args={args}, kwargs={kwargs})")
        
        # owner = the page that this widget belongs to, which is not 
        #           necessarily the parent. (The parent could be a 
        #           different container widget that we don't care
        #           about except for how it makes the page look.)
        self.owner = kwargs.pop('owner', None)

        # page_state_key = the key to store/retrieve data to/from in
        #           the page's dictionary
        self.page_state_key = kwargs.pop('key', None)

        # page_state_value = for sets of widgets that all share the same
        #           key (e.g., radio buttons), what value to use if this
        #           particular widget is selected
        self.page_state_value = kwargs.pop('value', None)

        # default_value = if there is no value for this widget's key, 
        #           use this value
        self.default_value = kwargs.pop('default', '')
        
        if self.owner is None:
            raise ValueError("required parameter: owner")
        if self.page_state_key is None:
            raise ValueError("required parameter: key")

        # This should call the 'other' inherited class' __init__, 
        # whatever it happens to be
        super().__init__(*args, **kwargs)

    @property
    def page_state(self):
        return self.owner.page_state

    @property
    def tab_state(self):
        return self.owner.tab_state


    def restore(self):
        # This is the method that the page should call to restore a widget
        self.blockSignals(True)
        self.restore_state()
        self.blockSignals(False)

    def restore_state(self):
        # This is where the meat of the widget's 'restore' functionality
        # should be implemented
        logger.debug(f"{self.__class__.__name__}.restore_state()")
    #}}}

class ZCheckBox(qtw.QCheckBox, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        super().__init__(*args, **kwargs)
        #self.owner = kwargs.pop('owner', None)
        #self.page_state_key = kwargs.pop('key', 'unnamed')

        #if self.owner is None:
        #    raise ValueError("required parameter: owner")

        #super().__init__(*args, **kwargs)
        
        #self.tab_state = self.owner.tab_state
        #self.page_state = self.owner.page_state

        self.toggled.connect(self.handle_changed)

        #self.restore()

    def handle_changed(self, status):
        self.page_state[self.page_state_key] = status
        #logger.debug(f"{self.__class__.__name__}.handle_changed")
        self.owner.update()

    def restore_state(self):
        super().restore_state()
        status = self.page_state.setdefault(self.page_state_key, False)
        self.setChecked(status)
    #}}}

class ZDateTimeEdit(qtw.QDateTimeEdit, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        #self.owner = kwargs.pop('owner', None)
        #self.page_state_key = kwargs.pop('key', 'unnamed')

        #if self.owner is None:
        #    raise ValueError("required parameter: owner")

        super().__init__(*args, **kwargs)

        #self.tab_state = self.owner.tab_state
        #self.page_state = self.owner.page_state
        
        self.setCalendarPopup(True)
        self.dateTimeChanged.connect(self.handle_changed)

        #self.restore()
    
    def handle_changed(self):
        self.page_state[self.page_state_key] = self.dateTime().toString()
        self.owner.update()

    def restore_state(self):
        super().restore_state()
        now = qtc.QDateTime.currentDateTime().toString()

        datetime = self.page_state.setdefault(self.page_state_key, now)

        self.setDateTime(
            qtc.QDateTime.fromString(datetime)
        )
    #}}}

class ZLabel(qtw.QLabel, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        #self.owner = kwargs.pop('owner', None)
        #self.page_state_key = kwargs.pop('key', 'unnamed')
        #self.default_value = kwargs.pop('default', '')
        # 
        #if self.owner is None:
        #    raise ValueError("required parameter: owner")

        super().__init__(*args, **kwargs)

        
        #self.page_state = self.owner.page_state
        #self.restore()

    def setText(self, txt):
        self.page_state[self.page_state_key] = txt
        super().setText(txt)
        self.owner.update()

    def restore_state(self):
        super().restore_state()
        txt = self.page_state.get(self.page_state_key, self.default_value)
        super().setText(txt)

    #}}}

class ZLineEdit(qtw.QLineEdit, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        #self.owner = kwargs.pop('owner', None)
        #self.page_state_key = kwargs.pop('key', 'unnamed')
        #self.default_value = kwargs.pop('default', '')

        #if self.owner is None:
        #    raise ValueError("required parameter: owner")

        super().__init__(*args, **kwargs)

        #self.tab_state = self.owner.tab_state
        #self.page_state = self.owner.page_state
        #self.textChanged.connect(self.owner.update)
        #self.editingFinished.connect(self.handle_changed)
        self.textChanged.connect(self.handle_changed)

        #self.restore()
    
    def handle_changed(self):
        self.page_state[self.page_state_key] = self.text()
        self.owner.update()

    def restore_state(self):
        super().restore_state()
        self.setText(self.page_state.setdefault(self.page_state_key, self.default_value))
    #}}}

class ZTextEdit(qtw.QTextEdit, LinkedWidget):
    #{{{
    editingFinished = qtc.pyqtSignal()
    receivedFocus = qtc.pyqtSignal()

    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        #self.owner = kwargs.pop('owner', None)
        #self.page_state_key = kwargs.pop('key', 'unnamed')
        
        #if self.owner is None:
        #    raise ValueError("required parameter: owner")

        super().__init__(*args, **kwargs)

        #self.tab_state = self.owner.tab_state
        #self.page_state = self.owner.page_state

        self._changed = False
        self.setTabChangesFocus(True)
        self.textChanged.connect(self._handle_text_changed)

        #self.editingFinished.connect(self.handle_editingFinished)
        #self.textChanged.connect(self.owner.update)
        self.textChanged.connect(self.handle_editingFinished)

        #self.restore()

    def handle_editingFinished(self):
        #self.page_state[self.page_state_key] = self.text()
        self.page_state[self.page_state_key] = self.document().toPlainText()
        self.owner.update()

    def restore_state(self):
        super().restore_state()
        self.setText(self.page_state.setdefault(self.page_state_key, ""))

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.receivedFocus.emit()

    def focusOutEvent(self, event):
        if self._changed:
            self.editingFinished.emit()
        super().focusOutEvent(event)

    def _handle_text_changed(self):
        self._changed = True

    def setTextChanged(self, state=True):
        self._changed = state
    #}}}

class ZRadioButton(qtw.QRadioButton, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        #self.owner = kwargs.pop('owner', None)
        #self.page_state_key = kwargs.pop('key', None)
        #self.page_state_value = kwargs.pop('value', None)
        
        #if self.owner is None:
        #    raise ValueError("required parameter: owner")
        #if self.page_state_key is None:
        #    raise ValueError("required parameter: key")
        #if self.page_state_value is None:
        #    raise ValueError("required parameter: value")
        
        super().__init__(*args, **kwargs)

        #self.tab_state = self.owner.tab_state
        #self.page_state = self.owner.page_state

        self.toggled.connect(self.handle_selected)

        #self.restore()

    def handle_selected(self):
        if self.isChecked():
            logger.debug(f"{self.page_state_key}/{self.page_state_value}: checked")
            self.page_state[self.page_state_key] = self.page_state_value
            self.owner.update()
            
    def restore_state(self):
        super().restore_state()
        if self.page_state.get(self.page_state_key, None) == self.page_state_value:
            self.setChecked(True)
        else:
            self.setChecked(False)

    #}}}

class ZRadioButtonGroup(qtw.QButtonGroup, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        #self.owner = kwargs.pop('owner', None)
        #self.page_state_key = kwargs.pop('key', None)
        #self.page_state_value = kwargs.pop('value', None)
        #self.default_value = kwargs.pop('default', None)
        
        #if self.owner is None:
        #    raise ValueError("required parameter: owner")
        #if self.page_state_key is None:
        #    raise ValueError("required parameter: key")

        super().__init__(*args, **kwargs)

        #self.tab_state = self.owner.tab_state
        #self.page_state = self.owner.page_state

        self.buttons = {}

    def button(self, value):
        if value in self.buttons.keys():
            return self.buttons[value]

    def create_button(self, value, caption=None):
        if value in self.buttons.keys():
            return self.buttons[value]

        new_button = ZRadioButton(owner=self.owner, 
                                    key=self.page_state_key, 
                                    value=value)
        if caption is not None:
            new_button.setText(caption)

        #new_button.toggled.connect(self.handle_changed)

        self.buttons[value] = new_button
        self.addButton(new_button)

        return new_button

    def handle_changed(self):
        pass # The buttons themselves handle this now
        #rb = self.sender()
        #
        #if not rb.isChecked():
        #    return

    def restore_state(self):
        super().restore_state()
        #logger.debug(f"{self.page_state_key}/{self.page_state_value}: restoring state")
        pass
    #}}}

class ZFileSelectWidget(qtw.QWidget, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        #self.owner = kwargs.pop('owner', None)
        self.button_text = kwargs.pop('button_text', 'select file')
        self.dialog_title = kwargs.pop('dialog_title', 'Select File')
        #self.page_state_key = kwargs.pop('key', 'unnamed')

        #if self.owner is None:
        #    raise ValueError("required parameter: owner")

        super().__init__(*args, **kwargs)

        #self.tab_state = self.owner.tab_state
        #self.page_state = self.owner.page_state

        self.button = qtw.QPushButton(self.button_text)
        self.button.setStyleSheet('''
                height: 15px;
                font-size: 10pt;
            ''')

        self.button.clicked.connect(self.select_file)
        self.filename_lineedit = qtw.QLineEdit()
        self.filename_lineedit.textChanged.connect(self.handle_changed)

        layout = qtw.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        layout.addWidget(self.button)
        layout.addWidget(self.filename_lineedit)

        #self.restore()

    def select_file(self):
        file_dialog = qtw.QFileDialog(self)
        file_dialog.setWindowTitle(self.dialog_title)

        if file_dialog.exec():
            self.filename_lineedit.blockSignals(True)
            self.filename_lineedit.setText(file_dialog.selectedFiles()[0])
            self.filename_lineedit.blockSignals(False)
        self.handle_changed()

    def handle_changed(self):
        self.page_state[self.page_state_key] = self.filename_lineedit.text()
        self.owner.update()

    def restore_state(self):
        super().restore_state()
        self.filename_lineedit.setText(self.page_state.get(self.page_state_key, ''))
    #}}}
