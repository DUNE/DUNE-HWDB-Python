#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

#{{{
from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from PyQt5.QtCore import QSize, Qt, pyqtSignal, pyqtSlot, QDateTime
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
)
#}}}

class PageWidget(QWidget):

    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        super().__init__(*args, **kwargs)
        self.workflow = self.parent()
        self.app_state = self.workflow.app_state
        self.tab_state = self.workflow.tab_state
        self.page_name = self.__class__.__name__.split('.')[-1]
        self.page_state = self.tab_state.setdefault(self.page_name, {})

        self.nav_bar = NavBar(workflow = self.workflow)

    def save(self):
        logger.debug(f"{self.__class__.__name__}.save()")

    def restore(self):
        logger.debug(f"{self.__class__.__name__}.restore()")

        if self.tab_state.get("part_id", None) is not None:
            #self.workflow.update_title(f"{self.tab_state['part_id']} - {self.page_name}")
            self.workflow.update_title(f"{self.tab_state['part_id']}\n{self.page_name}")
        else:
            self.workflow.update_title(f"{self.page_name}")

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

class NavBar(QWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")

        self.workflow = kwargs.pop('workflow', None)
        if self.workflow is None:
            raise ValueError("required parameter: workflow")

        super().__init__(*args, **kwargs)

        nav_layout = QHBoxLayout()

        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.workflow.navigate_prev)

        self.continue_button = QPushButton("Continue")
        self.continue_button.clicked.connect(self.workflow.navigate_next)

        nav_layout.addWidget(self.back_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.continue_button)

        self.setLayout(nav_layout)
    #}}}

class ZCheckBox(QCheckBox):
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        self.owner = kwargs.pop('owner', None)
        self.page_state_key = kwargs.pop('key', 'unnamed')

        if self.owner is None:
            raise ValueError("required parameter: owner")

        super().__init__(*args, **kwargs)
        
        self.tab_state = self.owner.tab_state
        self.page_state = self.owner.page_state

        self.toggled.connect(self.handle_changed)

        self.restore_state()

    def handle_changed(self, status):
        self.page_state[self.page_state_key] = status
        #logger.debug(f"{self.__class__.__name__}.handle_changed")
        self.owner.update()

    def restore_state(self):
        self.blockSignals(True)
        status = self.page_state.setdefault(self.page_state_key, False)
        self.setChecked(status)
        self.blockSignals(False)
    #}}}

class ZDateTimeEdit(QDateTimeEdit):
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        self.owner = kwargs.pop('owner', None)
        self.page_state_key = kwargs.pop('key', 'unnamed')

        if self.owner is None:
            raise ValueError("required parameter: owner")

        super().__init__(*args, **kwargs)

        self.tab_state = self.owner.tab_state
        self.page_state = self.owner.page_state
        
        self.setCalendarPopup(True)
        self.dateTimeChanged.connect(self.handle_changed)

        self.restore_state()
    
    def handle_changed(self):
        self.page_state[self.page_state_key] = self.dateTime().toString()
        self.owner.update()

    def restore_state(self):
        self.blockSignals(True)
        now = QDateTime.currentDateTime().toString()

        datetime = self.page_state.setdefault(self.page_state_key, now)

        self.setDateTime(
            QDateTime.fromString(datetime)
        )
        self.blockSignals(False)
    #}}}

class ZLabel(QLabel):
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        self.owner = kwargs.pop('owner', None)
        self.page_state_key = kwargs.pop('key', 'unnamed')
        self.default_value = kwargs.pop('default', '')
        
        if self.owner is None:
            raise ValueError("required parameter: owner")

        super().__init__(*args, **kwargs)

        
        self.page_state = self.owner.page_state
        self.restore_state()

    def setText(self, txt):
        self.page_state[self.page_state_key] = txt
        super().setText(txt)
        self.owner.update()

    def restore_state(self):
        txt = self.page_state.get(self.page_state_key, self.default_value)
        super().setText(txt)

    #}}}

class ZLineEdit(QLineEdit):
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        self.owner = kwargs.pop('owner', None)
        self.page_state_key = kwargs.pop('key', 'unnamed')
        self.default_value = kwargs.pop('default', '')

        if self.owner is None:
            raise ValueError("required parameter: owner")

        super().__init__(*args, **kwargs)

        self.tab_state = self.owner.tab_state
        self.page_state = self.owner.page_state
        #self.textChanged.connect(self.owner.update)
        #self.editingFinished.connect(self.handle_changed)
        self.textChanged.connect(self.handle_changed)

        self.restore_state()
    
    def handle_changed(self):
        self.page_state[self.page_state_key] = self.text()
        self.owner.update()

    def restore_state(self):
        self.blockSignals(True)
        self.setText(self.page_state.setdefault(self.page_state_key, self.default_value))
        self.blockSignals(False)
    #}}}

class ZTextEdit(QTextEdit):
    #{{{
    editingFinished = pyqtSignal()
    receivedFocus = pyqtSignal()

    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        self.owner = kwargs.pop('owner', None)
        self.page_state_key = kwargs.pop('key', 'unnamed')
        
        if self.owner is None:
            raise ValueError("required parameter: owner")

        super().__init__(*args, **kwargs)

        self.tab_state = self.owner.tab_state
        self.page_state = self.owner.page_state

        self._changed = False
        self.setTabChangesFocus(True)
        self.textChanged.connect(self._handle_text_changed)

        #self.editingFinished.connect(self.handle_editingFinished)
        #self.textChanged.connect(self.owner.update)
        self.textChanged.connect(self.handle_editingFinished)

        self.restore_state()

    def handle_editingFinished(self):
        #self.page_state[self.page_state_key] = self.text()
        self.page_state[self.page_state_key] = self.document().toPlainText()
        self.owner.update()

    def restore_state(self):
        self.blockSignals(True)
        self.setText(self.page_state.setdefault(self.page_state_key, ""))
        self.blockSignals(False)

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

class ZRadioButton(QRadioButton):
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        self.owner = kwargs.pop('owner', None)
        self.page_state_key = kwargs.pop('key', None)
        self.page_state_value = kwargs.pop('value', None)
        
        if self.owner is None:
            raise ValueError("required parameter: owner")
        if self.page_state_key is None:
            raise ValueError("required parameter: key")
        if self.page_state_value is None:
            raise ValueError("required parameter: value")
        
        super().__init__(*args, **kwargs)

        self.tab_state = self.owner.tab_state
        self.page_state = self.owner.page_state

        self.toggled.connect(self.handle_selected)

        self.restore_state()

    def handle_selected(self):
        if self.isChecked():
            logger.debug(f"{self.page_state_key}/{self.page_state_value}: checked")
            self.page_state[self.page_state_key] = self.page_state_value
            self.owner.update()
            
    def restore_state(self):
        self.blockSignals(True)
        #logger.debug(f"{self.page_state_key}/{self.page_state_value}: restoring state")
        if self.page_state.get(self.page_state_key, None) == self.page_state_value:
            self.setChecked(True)
        else:
            self.setChecked(False)

        self.blockSignals(False)
    #}}}

class ZRadioButtonGroup(QButtonGroup):
    #{{{
    def __init__(self, *args, **kwargs):
        logger.debug(f"{self.__class__.__name__}.__init__()")
        self.owner = kwargs.pop('owner', None)
        self.page_state_key = kwargs.pop('key', None)
        self.page_state_value = kwargs.pop('value', None)
        self.default_value = kwargs.pop('default', None)
        
        if self.owner is None:
            raise ValueError("required parameter: owner")
        if self.page_state_key is None:
            raise ValueError("required parameter: key")

        super().__init__(*args, **kwargs)

        self.tab_state = self.owner.tab_state
        self.page_state = self.owner.page_state

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
        #logger.debug(f"{self.page_state_key}/{self.page_state_value}: restoring state")
        pass
    #}}}



