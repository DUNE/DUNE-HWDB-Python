#!/usr/bin/env python

from Sisyphus.Configuration import config, USER_SETTINGS_DIR
logger = config.getLogger(__name__)

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw


class TabWidget(qtw.QTabWidget):
    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop("owner", None)
        if not self.owner:
            raise ValueError("required parameter: owner")
        self.application = self.owner

        super().__init__(*args, **kwargs)

        #self.setStyleSheet("min-height: 40px; max-height: 40px")
        self.setTabsClosable(True)

        self.tabCloseRequested.connect(self.application.close_tab)
        self.currentChanged.connect(self.application.on_currentChanged)

