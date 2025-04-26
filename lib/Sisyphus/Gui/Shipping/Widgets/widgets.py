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

from Sisyphus.Gui import DataModel as dm
from Sisyphus.Utils.Terminal.Style import Style
import json
import os
from copy import copy
import time

from .LinkedWidget import LinkedWidget

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
        txt = self.source() or self.default_value
        
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

