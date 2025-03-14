#!/usr/bin/env python
from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

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

class PageWidget(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workflow = self.parent()
        self.tab_state = self.workflow.tab_state
        self.page_name = self.__class__.__name__.split('.')[-1]
        self.page_state = self.tab_state.setdefault(self.page_name, {})

    def save(self):
        logger.debug("PageWidget.save()")

    def restore(self):
        logger.debug("PageWidget.restore()")

        if self.tab_state.get("part_id", None) is not None:
            self.workflow.update_title(f"{self.tab_state['part_id']} - {self.page_name}")

    def on_navigate_next(self):
        logger.debug(f"{self.__class__.__name__}.on_navigate_next()")
        ...

    def on_navigate_prev(self):
        logger.debug(f"{self.__class__.__name__}.on_navigate_prev()")
        ...

class ZCheckBox(QCheckBox):
    def __init__(self, *args, **kwargs):
        self.page_state_key = kwargs.pop('key', 'unnamed')
        super().__init__(*args, **kwargs)

        if self.parent() is None:
            return

        self.tab_state = self.parent().tab_state
        self.page_state = self.parent().page_state

        self.toggled.connect(self.handle_toggled)

        self.restore_state()

    def handle_toggled(self, status):
        self.page_state[self.page_state_key] = status

    def restore_state(self):
        status = self.page_state.setdefault(self.page_state_key, False)
        self.setChecked(status)



class ZLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        self.page_state_key = kwargs.pop('key', 'unnamed')
        super().__init__(*args, **kwargs)

        if self.parent() is None:
            return

        self.tab_state = self.parent().tab_state
        self.page_state = self.parent().page_state
        self.editingFinished.connect(self.update_state)

        self.restore_state()

    def update_state(self):
        self.page_state[self.page_state_key] = self.text()

    def restore_state(self):
        self.setText(self.page_state.setdefault(self.page_state_key, ""))

class ZTextEdit(QTextEdit):
    editingFinished = pyqtSignal()
    receivedFocus = pyqtSignal()

    def __init__(self, *args, **kwargs):
        self.page_state_key = kwargs.pop('key', 'unnamed')
        super().__init__(*args, **kwargs)

        if self.parent() is None:
            return

        self.tab_state = self.parent().tab_state
        self.page_state = self.parent().page_state

        self._changed = False
        self.setTabChangesFocus(True)
        self.textChanged.connect(self._handle_text_changed)

        self.editingFinished.connect(self.update_state)

        self.restore_state()

    def update_state(self):
        #self.page_state[self.page_state_key] = self.text()
        self.page_state[self.page_state_key] = self.document().toPlainText()

    def restore_state(self):
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





