#!/usr/bin/env python

import sys, os
#_libpath = os.path.join(os.path.normpath(os.path.dirname(__file__)), 'lib')
#sys.path.append(_libpath)
#print(sys.path)

from Sisyphus.Configuration import config, USER_SETTINGS_DIR
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut
from Sisyphus.Utils.Terminal.Style import Style

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib import units
    _reportlab_available = True

except ModuleNotFoundError:
    _reportlab_available = False



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

from pathlib import Path
import sys, os
import json
from copy import deepcopy


from Sisyphus.Gui.Shipping.Workflow import Workflow, NEW_TAB_STATE



# D00599800007
# D00502000040-00017

#SHIPPING_DATA_PATH = os.path.join(USER_SETTINGS_DIR, "shipping")
SHIPPING_DATA_PATH = USER_SETTINGS_DIR
APPLICATION_STATE_PATH = os.path.join(SHIPPING_DATA_PATH, "application_state.json")

class ShippingApplication(QApplication):
    #{{{
    def __init__(self, argv=None):
        super().__init__(argv)

        try:
            style_path = Sisyphus.get_path('resources/style.qss')
            self.setStyleSheet(Path(style_path).read_text())
        except FileNotFoundError as exc:
            msg = "Stylesheet not found. Using default style."
            Style.error.print(msg)
            logger.error(msg)


        #print("creating main window")
        self.main_window = MainWindow(app_state=self)

        self.tab_widget = self.main_window.tab_widget
        #self.tab_widget.currentChanged.connect(self.save_state)

        self.load_state()
        self.restore_tabs()

    def reset_state(self):
        self.app_state = {
            "tabs": [
                deepcopy(NEW_TAB_STATE)
            ]
        }

    def load_state(self):
        logger.debug("Loading application state")
        try:
            with open(APPLICATION_STATE_PATH, 'r') as fp:
                self.app_state = json.load(fp)
        except FileNotFoundError as exc:
            # not found = this is the first run. No problem.
            # just create the file.
            with open(APPLICATION_STATE_PATH, 'w') as fp:
                self.reset_state()
                self.save_state()
        except Exception as exc:
            # some other error. assume the file is corrupt
            # and overwrite it.
            msg = ("The application state appears to be corrupted. "
                        "Starting with fresh application state.")
            Style.error.print(msg)
            logger.error(msg)

            with open(APPLICATION_STATE_PATH, 'w') as fp:
                self.reset_state()
                self.save_state()

    def save_state(self):
        logger.debug("Saving application state")
        all_tabs_state = []
        for idx in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(idx)
            tab_state = tab.tab_state
            all_tabs_state.append(deepcopy(tab_state))

        self.app_state['tabs'] = all_tabs_state
        self.app_state['current_tab'] = self.tab_widget.currentIndex()

        with open(APPLICATION_STATE_PATH, 'w') as fp:
            json.dump(self.app_state, fp, indent=4)


    def restore_tabs(self):
        while self.tab_widget.count():
            self.tab_widget.removeTab(0)


        for tab_state in self.app_state['tabs']:
            self.create_tab(tab_state, save_after_creation=False)

        curr_idx = self.app_state.get('current_tab', 0)
        if self.tab_widget.count() > 0:
            self.tab_widget.setCurrentIndex(curr_idx)


    def create_tab(self, tab_state, save_after_creation=True):

        new_tab = Workflow(app=self, app_state=self.app_state, tab_state=tab_state)
        self.tab_widget.addTab(new_tab, "new tab")
        idx = self.tab_widget.indexOf(new_tab)

        new_tab.update_title(new_tab.title)
        
        if save_after_creation:
            self.save_state()

    def exit(self):
        self.save_state()
        self.main_window.close()
    #}}}

class MainWindow(QMainWindow):
    #{{{
    def __init__(self, app_state):
        #{{{
        super().__init__()
        self.app_state = app_state

        self.setWindowTitle('DUNE Shipping Tracker')

        self.setMinimumSize(QSize(800, 800))
        self.setMaximumSize(QSize(1920, 1080))

        self._create_menu_bar()
        self.tab_widget = WorkflowTabWidget(self)
        self.setCentralWidget(self.tab_widget)
        self.status_bar = self.statusBar()
        self.show()
        #}}}

    def _create_menu_bar(self):
        #{{{        
        menu_bar = self.menuBar()
        
        file_menu = menu_bar.addMenu("File")
        menu_bar.addMenu(file_menu)

        new_action = QAction(QIcon('./assets/new.png'), '&New', self)
        new_action.setStatusTip('Start New Shipping Workflow')
        #new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.app_state.create_tab)
        file_menu.addAction(new_action)

        file_menu.addSeparator()

        # exit menu item
        exit_action = QAction(QIcon('./assets/exit.png'), '&Exit', self)
        exit_action.setStatusTip('Exit')
        exit_action.setShortcut('Alt+F4')
        #exit_action.triggered.connect(self.quit)
        exit_action.triggered.connect(self.app_state.exit)
        file_menu.addAction(exit_action)
        #}}}

    def closeEvent(self, event):
        #print("User has clicked the red x on the main window")
        self.app_state.save_state()
        event.accept()
    #}}} 

class WorkflowTabWidget(QTabWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setTabsClosable(True)

        self.tabCloseRequested.connect(self.close_tab)

        #tab = Workflow(parent=self)

        #self.addTab(tab, "new shipping workflow")

    def close_tab(self, currentIndex):
        current_widget = self.widget(currentIndex)
        current_widget.deleteLater()
        self.removeTab(currentIndex)

    #}}}

if __name__ == '__main__':
    Style.info.print("The program is starting up. This may take a moment...")
    
    app = ShippingApplication(sys.argv)

    print("entering event loop -- window should show in a few seconds")
    print("(On WSL/Ubuntu under Windows, this sometimes takes a minute on the first run.\n"
            "Occasionally, it will not show at all, in which case, you may need to restart\n"
            "WSL. Other Linux setups may have different behaviors.)")
    logger.info("Entering event loop")
    app.exec()
    logger.info("Exiting event loop")

    Style.info.print("Exiting program")




