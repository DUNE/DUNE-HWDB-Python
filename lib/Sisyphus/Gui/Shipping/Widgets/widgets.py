#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)
#logger.setLevel("INFO")

HLD = highlight = "[bg=#999999,fg=#ffffff]"
HLI = highlight = "[bg=#009900,fg=#ffffff]"
HLW = highlight = "[bg=#999900,fg=#ffffff]"
HLE = highlight = "[bg=#990000,fg=#ffffff]"

from Sisyphus.Gui import DataModel as dm
from Sisyphus.Utils.Terminal.Style import Style
import json
import os
from copy import copy
import time

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtGui as qtg

###############################################################################

STYLE_LARGE_BUTTON = """
    font-size: 12pt;
    padding: 5px 15px;
"""

STYLE_SMALL_BUTTON = """
    padding: 5px 15px;
"""

class PageWidget(qtw.QWidget):
    #{{{

    # Override this on pages where a workflow is complete and there's no
    # sense in asking the user if they are sure before closing.
    _warn_before_closing = True

    def __init__(self, *args, **kwargs):
        logger.debug(f"[{self.__class__.__name__}].__init__()")

        self.workflow = kwargs.pop("workflow", None)
        if self.workflow is None:
            raise ValueError("required paramter: workflow")

        self.application = self.workflow.application

        super().__init__(*args, **kwargs)
        self._application_state = self.workflow.application_state
        self._workflow_state = self.workflow.workflow_state
        self.page_id = self.__class__.__name__.split('.')[-1]

        self.title_bar = TitleBar(page=self)
        self.nav_bar = NavBar(page=self)

        # Make the PageWidget's layout be a stacked layout that contains
        # the "real" widget containing the actual page contents, and
        # a hidden overlay that only shows up when the application is 
        # waiting for something from the database.
        self.master_layout = qtw.QStackedLayout()
        self.master_layout.setStackingMode(qtw.QStackedLayout.StackAll)
        super().setLayout(self.master_layout)
        self.main_widget = qtw.QWidget()
        self.overlay = WaitOverlay()
        self.master_layout.addWidget(self.overlay)
        self.master_layout.addWidget(self.main_widget)
        self.master_layout.setCurrentWidget(self.main_widget)
        self._wait_count = 0

    def setLayout(self, layout):
        # Re-interpret "setLayout" to mean for the main_widget instead
        # of for the entire PageWidget.
        self.main_widget.setLayout(layout)

    def wait(self):
        # Returns a very simple context manager that shows and
        # hides the overlay. It's better to use this than to use
        # the "start_waiting" and "stop_waiting" methods because
        # the context manager guarantees that the overlay will be
        # hidden when the task is finished, even if an exception
        # is raised.
        page = self
        class wait_mgr:
            def __enter__(self):
                page._wait_count += 1
                page.start_waiting()
            def __exit__(self, type, value, traceback):
                page._wait_count -= 1
                if page._wait_count <= 0:
                    page.stop_waiting()
        return wait_mgr()
                

    def start_waiting(self):
        # Show the overlay
        self.master_layout.setCurrentWidget(self.overlay)
        self.application.processEvents()
    
    def stop_waiting(self):
        # Hide the overlay
        self.master_layout.setCurrentWidget(self.main_widget)
        self.application.processEvents()
    


    @property
    def page_name(self):
        try:
            return self._page_name
        except AttributeError:
            logger.warning(f"{self.__class__.__name__} page_name not set!")
            self._page_name = self.page_id
            return self._page_name

    @page_name.setter
    def page_name(self, value):
        self._page_name = value

    @property
    def page_short_name(self):
        try:
            return self._page_short_name
        except AttributeError:
            logger.warning("page_short_name not set!")
            self._page_short_name = self.page_name
            return self._page_short_name

    @property
    def part_id(self):
        return self.workflow_state.get("part_info", {}).get("part_id", None)

    @property
    def application_state(self):
        return self.workflow.application_state

    @property
    def workflow_state(self):
        return self.workflow.workflow_state

    @workflow_state.setter
    def workflow_state(self, value):
        self.workflow.workflow_state = value
        return value

    @property
    def page_state(self):
        return self.workflow.workflow_state.setdefault(self.page_id, {})

    def save(self):
        logger.debug(f"{self.__class__.__name__}.save()")
        self.workflow.save()

    @property
    def tab_title(self):
        if self.part_id is not None:
            tab_title = f"{self.part_id}\n{self.page_short_name}"
        else:
            tab_title = f"{self.page_short_name}"
        return tab_title

    def activate(self):
        # call when switching to this page
        logger.info(f"{HLD}{self.__class__.__name__}.activate()")
        logger.info(f"(workflow init: {self.workflow._finished_init})")
        self.restore()
        self.refresh()
        self.application.update_status(self.page_name)

    def restore(self):
        for linked_widget in self.findChildren(LinkedWidget):
            linked_widget.restore()

    def refresh(self):
        # overload this method to add an action when the content of the page
        # has changed, e.g., to enable/disable nav buttons
        logger.info(f"{HLI}{self.__class__.__name__}.refresh()")
        self.title_bar.page_subtitle.restore()

    def on_navigate_next(self):
        logger.debug(f"{HLD}{self.__class__.__name__}.on_navigate_next()")
        self.save()
        return True

    def on_navigate_prev(self):
        logger.debug(f"{HLD}{self.__class__.__name__}.on_navigate_prev()")
        self.save()
        return True


    def close_tab_requested(self):
        # The user is trying to close this tab. Ask them if they are sure.
        # Return True if it's okay to close, or False if they changed their mind.

        logger.error(f"close_tab_requested, _warn_berfore_closing: {self._warn_before_closing}")
        logger.error(f"my class is: {self.__class__.__name__}")
        if self.__class__._warn_before_closing:
 
            retval = qtw.QMessageBox.warning(
                        self.application.main_window,
                        "Warning",
                        "If you remove this workflow, you will not be able to return to it. "
                                "Are you sure you want to remove this workflow?",
                        qtw.QMessageBox.Ok | qtw.QMessageBox.Cancel)

            confirm_remove_tab = retval == qtw.QMessageBox.Ok

            if confirm_remove_tab:
                logger.info("The user elected to close this tab.")
            else:
                logger.info("The user decided to keep the tab.")
        else:
            logger.info("This tab will close. No confirmation required.")
            confirm_remove_tab = True

        return confirm_remove_tab

    #}}}

class WaitOverlay(qtw.QWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.vertical_layout = qtw.QVBoxLayout()
        self.horizontal_layout = qtw.QHBoxLayout()

        self.overlay_widget = qtw.QLabel("Please Wait...")
        self.overlay_widget.setStyleSheet(
                "font-size: 20pt; "
                "background-color: rgba(0, 0, 0, 64); ")
        self.overlay_widget.setAlignment(qtc.Qt.AlignCenter)
        self.overlay_widget.setMinimumSize(qtc.QSize(400, 300))
        
        self.horizontal_layout.addStretch()
        self.horizontal_layout.addWidget(self.overlay_widget)
        self.horizontal_layout.addStretch()

        self.vertical_layout.addStretch()
        self.vertical_layout.addLayout(self.horizontal_layout)
        self.vertical_layout.addStretch()

        self.setLayout(self.vertical_layout)
    #}}}


class TitleBar(qtw.QWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        #logger.debug(f"{self.__class__.__name__}.__init__()")

        self.page = kwargs.pop('page', None)        
        if self.page is None:
            raise ValueError("required parameter: page")

        super().__init__(*args, **kwargs)
        
        main_layout = qtw.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.page_title = qtw.QLabel(self.page.page_name)
        self.page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        self.page_title.setAlignment(qtc.Qt.AlignCenter)

        main_layout.addWidget(self.page_title)

        self.page_subtitle = ZLabel(
                        page=self.page, 
                        key='subtitle', 
                        source='attr:part_id',
                        default='[no part_id yet]')
        self.page_subtitle.setAlignment(qtc.Qt.AlignCenter)
        
        main_layout.addWidget(self.page_subtitle)

        self.setLayout(main_layout)
    #}}}

class NavBar(qtw.QWidget):
    #{{{
    def __init__(self, *args, **kwargs):

        self.page = kwargs.pop('page', None)
        if self.page is None:
            raise ValueError("required parameter: page")
        self.workflow = self.page.workflow
        self.application = self.page.application

        super().__init__(*args, **kwargs)

        main_layout = qtw.QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.back_button = qtw.QPushButton("Back")
        self.back_button.setStyleSheet(STYLE_LARGE_BUTTON)
        self.back_button.clicked.connect(self.page.workflow.navigate_prev)

        self.continue_button = qtw.QPushButton("Continue")
        self.continue_button.setStyleSheet(STYLE_LARGE_BUTTON)
        self.continue_button.clicked.connect(self.page.workflow.navigate_next)

        self.close_tab_button = qtw.QPushButton("Close Tab")
        self.close_tab_button.setStyleSheet(STYLE_LARGE_BUTTON)
        #self.close_tab_button.clicked.connect(self.application.close_tab)
        self.close_tab_button.clicked.connect(
                        lambda: self.application.close_tab_by_obj(self.workflow))

        main_layout.addWidget(self.back_button)
        main_layout.addStretch()
        main_layout.addWidget(self.close_tab_button)
        main_layout.addWidget(self.continue_button)
        self.close_tab_button.setVisible(False)


        self.setLayout(main_layout)

    def set_buttons(self, button_list):
        button_list = copy(button_list)

        if 'back' in button_list:
            self.back_button.setVisible(True)
        else:
            self.back_button.setVisible(False)

        if 'continue' in button_list:
            self.continue_button.setVisible(True)
        else:
            self.continue_button.setVisible(False)

        if 'close' in button_list:
            self.close_tab_button.setVisible(True)
        else:
            self.close_tab_button.setVisible(False)


    #}}}



class LinkedWidget:
    #{{{
    def __init__(self, *args, **kwargs):
        #{{{
        #logger.debug(f"{self.__class__.__name__}.__init__()")
 
        # page = the page that this widget belongs to, which is not 
        #           necessarily the parent. (The parent could be a 
        #           different container widget that we don't care
        #           about except for how it makes the page look.)
        self.page = kwargs.pop('page', None)
        self.workflow = self.page.workflow
        self.application = self.page.application

        # state_key = the key to store/retrieve data to/from in
        #           the page's dictionary
        self.state_key = kwargs.pop('key', None)

        # state_value_when_selected = for sets of widgets that all share the same
        #           key (e.g., radio buttons), what value to use if this
        #           particular widget is selected
        self.state_value_when_selected = kwargs.pop('value', None)

        # default_value = if there is no value for this widget's key, 
        #           use this value
        self.default_value = kwargs.pop('default', '')

        # source_key = a place to look for additional data outside of the
        #           page state
        self.source_key = kwargs.pop('source', None)
        
        if self.page is None:
            raise ValueError("required parameter: page")
        if self.state_key is None:
            raise ValueError("required parameter: key")

        # This should call the 'other' inherited class' __init__, 
        # whatever it happens to be
        super().__init__(*args, **kwargs)
        self.setObjectName(__class__.__name__)       
        #}}}

    def source(self):
        if self.source_key is None:
            return None

        parts = self.source_key.split(':')

        if len(parts) == 1:
            # If there's only one part, treat it pretty much the same
            # as a state_key, i.e., something stored on this page
            return self.page_state[parts[0]]

        if parts[0] == 'attr':
            if len(parts) != 2:
                raise KeyError("attr key has too many parts")
            # If the format is "attr:<key>", get the value of an 
            # attribute in the page object itself, and not the 
            # page state. E.g., "attr:part_id" would look for
            # self.page.part_id
            return getattr(self.page, parts[1], None)

        if parts[0] == 'workflow':
            if parts[1] == 'attr':
                if len(parts) == 2:
                    raise KeyError(f"{key!r} workflow:attr key missing 3rd part")
                elif len(parts) > 3:
                    raise KeyError(f"{key!r} workflow:attr key has too many parts")
                # If the format is "workflow:attr:<key>", get the value
                # of the attribute in the workflow object, e.g., 
                # "workflow:attr:part_info" would look for
                # self.workflow.part_info
                return getattr(self.workflow, parts[2], None)
            else:
                # Determine if the part after "workflow" refers to a page_id
                # or not.
                other_page = self.page.workflow.get_page_by_id(parts[1])

                if other_page is None:
                    if len(parts) != 2:
                        raise KeyError(f"{key!r} workflow:<key> has too many parts")
                    # If the format is "workflow:<key>" and <key> does NOT
                    # refer to a page_id, then get <key> from the workflow
                    # state
                    return self.workflow_state.get(parts[1], None)

                if len(parts) < 3:
                    raise KeyError(f"{key!r} workflow:<page> key needs at least 3 parts")
                if parts[2] == "attr":
                    if len(parts) != 4:
                        raise KeyError(f"{key!r} workflow:<page>:attr key needs 4 parts")
                    # If the format is "workflow:<page_id>:attr:<key>", 
                    # return the attribute from the page it's referring to.
                    return getattr(other_page, parts[3], None)
                else:
                    if len(parts) != 3:
                        raise KeyError(f"{key!r} workflow:<page>:<key> key needs 3 parts")
                    # If the format is "workflow:<page_id>:<key>", get the
                    # value from the page_state of the page it's referring to.
                    return other_page.page_state[parts[2]]

        if parts[0] == 'application':
            if parts[1] == 'attr':
                if len(parts) != 3:
                    raise KeyError(f"{key!r} application:attr key needs 3 parts")
                # If the format is "application:<attr>:<key>, get the value
                # from the application object
                return getattr(self.application, parts[2], None)
            else:
                if len(parts) != 2:
                    raise KeyError(f"{key!r} application:<key> key has too many parts")
                # If the format is "application:<key>", get the value from
                # the application_state
                return self.application_state.get(parts[1], None)

    @property
    def page_state(self):
        return self.page.page_state

    @property
    def workflow_state(self):
        return self.page.workflow_state

    @property
    def application_state(self):
        return self.page.application_state

    def restore(self):
        # This is the method that the page should call to restore a widget
        # but it should not be overloaded unless necessary
        self.blockSignals(True)
        self.restore_state()
        self.blockSignals(False)

    def restore_state(self):
        # Overload this one!
        # This is where the meat of the widget's 'restore' functionality
        # should be implemented
        logger.debug(f"{self.__class__.__name__}.restore_state()")
    #}}}

class ZPartDetails(qtw.QWidget, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.pid_label = qtw.QLabel("<not set>")
        self.part_name_label = qtw.QLabel("<not set>")
        self.system_label = qtw.QLabel("<not set>")
        self.subsystem_label = qtw.QLabel("<not set>")

        self.show_empty_slots = qtw.QCheckBox("show vacant slots")
        self.show_empty_slots.toggled.connect(self.on_show_empty_slots_checked)

        self._setup_UI()

    def on_show_empty_slots_checked(self, status):
        self.page_state[self.state_key] = status
        self.restore_state()
        self.page.refresh()

    def _setup_UI(self):
        #{{{
        # The "more obvious" way of doing this is to just make this widget
        # inherit from QFrame instead of QWidget, but for some reason, it
        # refuses to draw the border in the dark or light style (though it
        # does work in other styles). So, we'll make this a QWidget that
        # contains a QFrame that contains the rest. >:-@

        self.main_layout = qtw.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self.frame = qtw.QFrame()
        self.frame.setFrameStyle(qtw.QFrame.Box | qtw.QFrame.Sunken)
        self.frame.setLineWidth(1)

        self.main_layout.addWidget(self.frame)

        grid_layout = qtw.QGridLayout()
        self.frame.setLayout(grid_layout)

        grid_layout.setContentsMargins(5, 5, 5, 5)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 2)
        grid_layout.setColumnStretch(2, 1)
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(0)

        top_right = qtc.Qt.AlignTop | qtc.Qt.AlignRight
        top_left = qtc.Qt.AlignTop | qtc.Qt.AlignLeft
        center_right = qtc.Qt.AlignVCenter | qtc.Qt.AlignRight
        center_left = qtc.Qt.AlignVCenter | qtc.Qt.AlignLeft
        top_center = qtc.Qt.AlignTop | qtc.Qt.AlignHCenter

        self.table = qtw.QTableWidget(0, 3)
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalHeaderLabels(['Sub-component PID',
                            'Component Type Name', 'Functional Position Name'])
        horizontal_header = self.table.horizontalHeader()
        horizontal_header.resizeSection(0, 200)
        horizontal_header.resizeSection(1, 260)
        horizontal_header.resizeSection(2, 260)


        current_row = 0

        grid_layout.addWidget(qtw.QLabel("PID"),
                            current_row, 0, 1, 1)
        grid_layout.addWidget(self.pid_label,
                            current_row, 1, 1, 1)
        current_row += 1

        grid_layout.addWidget(qtw.QLabel("Part Type Name"),
                            current_row, 0, 1, 1)
        grid_layout.addWidget(self.part_name_label,
                            current_row, 1, 1, 1)
        current_row += 1

        grid_layout.addWidget(qtw.QLabel("System"),
                            current_row, 0, 1, 1)
        grid_layout.addWidget(self.system_label,
                            current_row, 1, 1, 1)
        current_row += 1

        grid_layout.addWidget(qtw.QLabel("Subsystem"),
                            current_row, 0, 1, 1)
        grid_layout.addWidget(self.subsystem_label,
                            current_row, 1, 1, 1)
        grid_layout.addWidget(self.show_empty_slots,
                            current_row, 2, 1, 1)
        current_row += 1


        grid_layout.setRowMinimumHeight(current_row, 10)
        current_row += 1


        grid_layout.addWidget(self.table,
                            current_row, 0, 1, 3)
        current_row += 1
        #}}}

    def restore_state(self):
        super().restore_state()
        show_empty_slots_status = self.page_state.setdefault(self.state_key, False)
        self.show_empty_slots.blockSignals(True)
        self.show_empty_slots.setChecked(show_empty_slots_status)
        self.show_empty_slots.blockSignals(False)

        self.table.setEditTriggers(qtw.QAbstractItemView.NoEditTriggers)

        source = self.source() or {}
        self.pid_label.setText(source.get('part_id', 'N/A'))
        self.part_name_label.setText(source.get('part_type_name', 'N/A'))
        self.system_label.setText(source.get('system', 'N/A'))
        self.subsystem_label.setText(source.get('subsystem', 'N/A'))

        subcomps = source.get('subcomponents', {})

        if show_empty_slots_status:
            connectors = source.get('connector_data', {})
            subcomps_by_func_pos = { v['Functional Position Name']: v
                            for v in subcomps.values() }

            self.table.setRowCount(len(connectors))
            for idx, (func_pos, connector_def) in enumerate(connectors.items()):
                part_type_id = connector_def['part_type_id']
                part_type_name = connector_def['part_type_name']

                if func_pos in subcomps_by_func_pos:
                    subcomp_is_empty = False
                    subcomp = subcomps_by_func_pos[func_pos]
                else:
                    subcomp_is_empty = True
                    subcomp = {
                        "Sub-component PID": "<empty>",
                        "Component Type Name": part_type_name,
                        "Functional Position Name": func_pos
                    }

                subcomp_pid_widget = qtw.QTableWidgetItem(subcomp['Sub-component PID'])
                subcomp_type_widget = qtw.QTableWidgetItem(subcomp['Component Type Name'])
                subcomp_func_pos_widget = qtw.QTableWidgetItem(subcomp['Functional Position Name'])


                if subcomp_is_empty:
                    #subcomp_pid_widget.setStyleSheet("color: #ff0000")
                    brush = qtg.QBrush()
                    color = qtg.QColor(255, 0, 0, 255)
                    brush.setColor(color)
                    subcomp_pid_widget.setForeground(brush)
                    subcomp_pid_widget.setBackground(brush)

                self.table.setItem(idx, 0, subcomp_pid_widget)
                self.table.setItem(idx, 1, subcomp_type_widget)
                self.table.setItem(idx, 2, subcomp_func_pos_widget)

        else:
            self.table.setRowCount(len(subcomps))
            for idx, subcomp in enumerate(subcomps.values()):
                self.table.setItem(idx, 0, qtw.QTableWidgetItem(subcomp['Sub-component PID']))
                self.table.setItem(idx, 1, qtw.QTableWidgetItem(subcomp['Component Type Name']))
                self.table.setItem(idx, 2, qtw.QTableWidgetItem(subcomp['Functional Position Name']))

    #}}}

class ZCheckBox(qtw.QCheckBox, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.toggled.connect(self.handle_changed)

    def handle_changed(self, status):
        self.page_state[self.state_key] = status
        self.page.refresh()

    def restore_state(self):
        super().restore_state()
        status = self.page_state.setdefault(self.state_key, False)
        self.setChecked(status)
    #}}}

class ZDateTimeEdit(qtw.QDateTimeEdit, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.setCalendarPopup(True)
        self.dateTimeChanged.connect(self.handle_changed)

    def handle_changed(self):
        self.page_state[self.state_key] = self.dateTime().toString(qtc.Qt.DateFormat.ISODate)
        self.page.refresh()

    def restore_state(self):
        super().restore_state()
        now = qtc.QDateTime.currentDateTime().toString(qtc.Qt.DateFormat.ISODate)

        # Note that it should already exist and has an initial value of
        # an empty string, so we have to actually look at it and decide
        # what to do, instead of doing a setdefault or something
        datetime = self.page_state.get(self.state_key, '')
        if datetime == '':
            datetime = now
            self.page_state[self.state_key] = datetime

        self.setDateTime(
            qtc.QDateTime.fromString(datetime, qtc.Qt.DateFormat.ISODate)
        )
    #}}}

class ZLabel(qtw.QLabel, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setText(self, txt):
        self.page_state[self.state_key] = txt
        super().setText(txt)

    def restore_state(self):
        super().restore_state()

        # Note: if you ever need this to work off the state_key like
        # every other LinkedWidget, you can put the desired state_key
        # into the source_key, and it will pull from there.
        txt = self.source()
        super().setText(txt)

    #}}}

class ZLineEdit(qtw.QLineEdit, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textChanged.connect(self.handle_changed)
    
    def handle_changed(self):
        self.page_state[self.state_key] = self.text()
        self.page.refresh()

    def restore_state(self):
        super().restore_state()
        self.setText(self.page_state.setdefault(self.state_key, self.default_value))
    #}}}

class ZTextEdit(qtw.QTextEdit, LinkedWidget):
    #{{{
    editingFinished = qtc.pyqtSignal()
    receivedFocus = qtc.pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._changed = False
        self.setTabChangesFocus(True)
        self.textChanged.connect(self._handle_text_changed)

        self.textChanged.connect(self.handle_editingFinished)

    def handle_editingFinished(self):
        self.page_state[self.state_key] = self.document().toPlainText()
        self.page.refresh()

    def restore_state(self):
        super().restore_state()
        self.setText(self.page_state.setdefault(self.state_key, ""))

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
        super().__init__(*args, **kwargs)
        self.toggled.connect(self.handle_selected)

    def handle_selected(self):
        if self.isChecked():
            logger.debug(f"{self.state_key}/{self.state_value_when_selected}: checked")
            self.page_state[self.state_key] = self.state_value_when_selected
            self.page.refresh()
            
    def restore_state(self):
        super().restore_state()
        if self.page_state.get(self.state_key, None) == self.state_value_when_selected:
            self.setChecked(True)
        else:
            self.setChecked(False)

    #}}}

class ZRadioButtonGroup(qtw.QButtonGroup, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buttons = {}

    def button(self, value):
        if value in self.buttons.keys():
            return self.buttons[value]
        raise KeyError(f"button {value!r} does not exist in ZRadioButtonGroup")

    def create_button(self, value, caption=None):
        if value in self.buttons.keys():
            return self.buttons[value]

        new_button = ZRadioButton(page=self.page, 
                                    key=self.state_key, 
                                    value=value)
        if caption is not None:
            new_button.setText(caption)

        self.buttons[value] = new_button
        self.addButton(new_button)

        return new_button

    def handle_changed(self):
        pass # The buttons themselves handle this now

    #}}}

class ZFileSelectWidget(qtw.QWidget, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        # We have to 'pop' these first, or __init__ on the underlying
        # QWidget will choke on them!
        self.button_text = kwargs.pop('button_text', 'select file')
        self.dialog_title = kwargs.pop('dialog_title', 'Select File')

        super().__init__(*args, **kwargs)

        self.button = qtw.QPushButton(self.button_text)
        self.button.setStyleSheet(STYLE_SMALL_BUTTON)

        self.button.clicked.connect(self.select_file)
        self.filename_lineedit = qtw.QLineEdit()
        self.filename_lineedit.setEnabled(False)
        self.filename_lineedit.textChanged.connect(self.handle_changed)

        main_layout = qtw.QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)
        main_layout.addWidget(self.button)
        main_layout.addWidget(self.filename_lineedit)

    def select_file(self):
        file_dialog = qtw.QFileDialog(self)
        file_dialog.setWindowTitle(self.dialog_title)

        if file_dialog.exec():
            self.filename_lineedit.blockSignals(True)
            self.filename_lineedit.setText(file_dialog.selectedFiles()[0])
            self.filename_lineedit.blockSignals(False)
        self.handle_changed()

    def handle_changed(self):
        self.page_state[self.state_key] = self.filename_lineedit.text()
        self.page.refresh()

    def restore_state(self):
        super().restore_state()
        self.filename_lineedit.setText(self.page_state.get(self.state_key, ''))
    #}}}

class ZInstitutionWidget(qtw.QWidget, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.institution_id = None
        self.country_code = None

        main_layout = qtw.QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)


        ### Country Widget
        country_widget = self.country_widget = qtw.QComboBox()
        country_widget.setStyleSheet("width: 200px")
        #country_widget.setEditable(True)
        country_widget.currentIndexChanged.connect(self.on_selectCountry)
        country_widget.setPlaceholderText("Select Country...")
        for country_code, country in self.get_countries().items():
            country_widget.addItem(country, country_code)
        #country_widget.setCurrentIndex(-1)
        main_layout.addWidget(country_widget)
        
        ### Institution Widget
        inst_widget = self.inst_widget = qtw.QComboBox()
        inst_widget.setStyleSheet("width: 400px")
        #inst_widget.setEditable(True)
        inst_widget.currentIndexChanged.connect(self.on_selectInstitution)
        self.inst_widget.setPlaceholderText("Select Institution...")
        main_layout.addWidget(self.inst_widget)

        main_layout.addStretch()
    
    def on_selectCountry(self):
        self.country_code = self.country_widget.currentData()

        self.inst_widget.clear()
        for inst_id, inst in self.get_insts(self.country_code).items():
            self.inst_widget.addItem(inst, inst_id)

        if self.institution_id in self.get_insts(self.country_code):
            self.inst_widget.setCurrentIndex(
                    self.inst_widget.findData(self.institution_id))
        else:
            self.institution_id = None
            


    def on_selectInstitution(self):
        self.institution_id = str(self.inst_widget.currentData())
        self.page_state[self.state_key] = str(self.institution_id)
        self.page.refresh()

    def restore_state(self):
        self.country_widget.blockSignals(True)
        self.inst_widget.blockSignals(True)
        
        self.institution_id = str(self.page_state.setdefault(
                                            self.state_key, self.default_value))
        self.country_code = self.get_country_of_inst(self.institution_id)
        
        if self.country_code:
            c_index = self.country_widget.findData(self.country_code)
            self.country_widget.setCurrentIndex(c_index)
            self.on_selectCountry()
            i_index = self.inst_widget.findData(self.institution_id)
            self.inst_widget.setCurrentIndex(i_index)
        else:        
            self.country_widget.setCurrentIndex(-1)
            self.inst_widget.setCurrentIndex(-1)
    
        self.country_widget.blockSignals(False)
        self.inst_widget.blockSignals(False)
        
        
    @classmethod
    def get_countries(cls):
        if not hasattr(cls, '_inst_cache'):
            cls._get_inst_data()
        return cls._inst_cache['countries']

    @classmethod
    def get_insts(cls, country_code):
        if not hasattr(cls, '_inst_cache'):
            cls._get_inst_data()
        return cls._inst_cache['insts'][country_code]
    
    @classmethod
    def get_country_of_inst(cls, inst_id):
        if not hasattr(cls, '_inst_cache'):
            cls._get_inst_data()
        return cls._inst_cache['country_by_inst'].get(inst_id, None)

    @classmethod
    def _get_inst_data(cls):
        #{{{
        if hasattr(cls, '_cache'):
            return cls._cache

        inst_data = dm.Institutions().data
        full_list = [ (f"({c_code}) {c_name}", f"({inst_id}) {inst_name}", c_code, inst_id)
                      for c_code, c_name, inst_name, inst_id in
                sorted(list(
                    [
                        (
                            inst['country']['code'],
                            inst['country']['name'],
                            inst['name'],
                            str(inst['id'])
                        ) for inst in inst_data 
                    ]
                ))
            ]
        country_list = {
                c_code: c_full_name for 
                    (c_full_name, inst_full_name, c_code, inst_id) in full_list
            }
        inst_list = {c_code_key:
                        {inst_id: inst_full_name
                            for (c_full_name, inst_full_name, c_code, inst_id) in full_list
                            if c_code_key == c_code}
                        for c_code_key in country_list.keys()}
        inst_list[None] = {}
        country_lookup_by_inst = {inst_id: c_code 
                            for (c_full_name, inst_full_name, c_code, inst_id) in full_list}
        cls._inst_cache = {
                "countries": country_list,
                "insts": inst_list,
                "country_by_inst": country_lookup_by_inst
            }
        #}}}
    #}}}

