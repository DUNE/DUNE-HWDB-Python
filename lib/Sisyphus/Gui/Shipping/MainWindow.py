#!/usr/bin/env python

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

HLD = highlight = "[bg=#999999,fg=#ffffff]"
HLI = highlight = "[bg=#009900,fg=#ffffff]"
HLW = highlight = "[bg=#999900,fg=#ffffff]"
HLE = highlight = "[bg=#990000,fg=#ffffff]"

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

from Sisyphus.Gui.Shipping.WorkflowWidget import WorkflowWidget
from Sisyphus.Gui.Shipping.TabWidget import TabWidget

class MainWindow(qtw.QMainWindow):
    def __init__(self, application):
        #{{{
        super().__init__()
        self.application = application

        self.setWindowTitle('DUNE Shipping Tracker')

        self.setMinimumSize(qtc.QSize(800, 800))
        #self.setMaximumSize(qtc.QSize(1920, 1080))
        #self.setMaximumSize(qtc.QSize(1200, 900))

        self._create_menu_bar()
        self.tab_widget = TabWidget(owner=self.application)

        self.setCentralWidget(self.tab_widget)


        #self.setCentralWidget(self.tab_widget)
        #self.status_bar = self.statusBar()
        self.show()
        #}}}

    def _create_menu_bar(self):
        #{{{        
        menu_bar = self.menuBar()
        
        options_menu = menu_bar.addMenu("Options")
        menu_bar.addMenu(options_menu)

        ################
        #new_action = qtw.QAction(QIcon('./assets/new.png'), '&New', self)
        new_action = qtw.QAction('&New Workflow', self)
        new_action.setStatusTip('Start New Shipping Workflow')
        #new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.application.create_new_tab)
        options_menu.addAction(new_action)
        ################

        config_action = qtw.QAction('&Configure...', self)
        config_action.setStatusTip('Change configuration for this application')
        config_action.triggered.connect(self.application.configure)
        options_menu.addAction(config_action)

        ################
        options_menu.addSeparator()
        ################

        # exit menu item
        #exit_action = qtw.QAction(QIcon('./assets/exit.png'), '&Exit', self)
        exit_action = qtw.QAction('&Exit', self)
        exit_action.setStatusTip('Exit')
        exit_action.setShortcut('Alt+F4')
        #exit_action.triggered.connect(self.quit)
        exit_action.triggered.connect(self.application.exit)
        options_menu.addAction(exit_action)

        if self.application._debug:
            debug_menu = menu_bar.addMenu("Debug")
            menu_bar.addMenu(debug_menu)

            #debug_info_action = qtw.QAction("debug info", self)
            #debug_info_action.triggered.connect(self.application.debug_info)
            #debug_info_action.setShortcut('F8')
            #debug_menu.addAction(debug_info_action)
            
            debug_appstate_action = qtw.QAction("app state", self)
            debug_appstate_action.triggered.connect(self.application.debug_app_state)
            debug_appstate_action.setShortcut('F8')
            debug_menu.addAction(debug_appstate_action)
            
            debug_tabstate_action = qtw.QAction("tab widget tree", self)
            debug_tabstate_action.triggered.connect(self.application.debug_tab_tree)
            debug_tabstate_action.setShortcut('F9')
            debug_menu.addAction(debug_tabstate_action)
            
            debug_pagestate_action = qtw.QAction("page widget tree", self)
            debug_pagestate_action.triggered.connect(self.application.debug_page_tree)
            debug_pagestate_action.setShortcut('F10')
            debug_menu.addAction(debug_pagestate_action)
        
            debug_test_action = qtw.QAction("test function", self)
            debug_test_action.triggered.connect(self.application.debug_test_function)
            debug_test_action.setShortcut('F11')
            debug_menu.addAction(debug_test_action)
                
        #}}}

    def closeEvent(self, event):
        #print("User has clicked the red x on the main window")
        #self.application.save_state()
        self.application.exit()
        event.accept()

