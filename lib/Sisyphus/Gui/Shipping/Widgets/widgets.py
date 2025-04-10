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

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

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
    def __init__(self, *args, **kwargs):
        logger.debug(f"[{self.__class__.__name__}].__init__()")

        self.owner = kwargs.pop("owner", None)
        if self.owner is None:
            raise ValueError("required paramter: owner")

        self.workflow = self.owner
        self.application = self.workflow.application

        super().__init__(*args, **kwargs)
        self._app_state = self.workflow.app_state
        self._workflow_state = self.workflow.workflow_state
        self.page_id = self.__class__.__name__.split('.')[-1]

        self.title_bar = TitleBar(owner = self)
        self.nav_bar = NavBar(owner = self)

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
    def app_state(self):
        return self.workflow.app_state

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
        self.update()
        self.application.update_status(self.page_name)

    def restore(self):
        for linked_widget in self.findChildren(LinkedWidget):
            linked_widget.restore()

    def update(self):
        # overload this method to add an action when the content of the page
        # has changed, e.g., to enable/disable nav buttons
        logger.info(f"{HLI}{self.__class__.__name__}.update()")
        self.title_bar.page_subtitle.restore()

    def on_navigate_next(self):
        logger.debug(f"{HLD}{self.__class__.__name__}.on_navigate_next()")
        self.save()
        return True

    def on_navigate_prev(self):
        logger.debug(f"{HLD}{self.__class__.__name__}.on_navigate_prev()")
        self.save()
        return True

    #@property
    #def working_directory(self):
    #    if self.part_id is None:
    #        retval = self.application.working_directory
    #    else:
    #        retval = os.path.normpath(
    #                        os.path.join(self.application.working_directory, self.part_id))
    #    os.makedirs(retval, exist_ok=True)
    #    return retval
    #}}}

class TitleBar(qtw.QWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        #logger.debug(f"{self.__class__.__name__}.__init__()")

        self.owner = kwargs.pop('owner', None)        
        if self.owner is None:
            raise ValueError("required parameter: owner")

        super().__init__(*args, **kwargs)
        
        main_layout = qtw.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.page_title = qtw.QLabel(self.owner.page_name)
        self.page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        self.page_title.setAlignment(qtc.Qt.AlignCenter)

        main_layout.addWidget(self.page_title)

        self.page_subtitle = ZLabel(owner=self.owner, key='attr:part_id', default='[no part_id yet]')
        self.page_subtitle.setAlignment(qtc.Qt.AlignCenter)
        
        main_layout.addWidget(self.page_subtitle)

        self.setLayout(main_layout)
    #}}}

class NavBar(qtw.QWidget):
    #{{{
    def __init__(self, *args, **kwargs):

        self.owner = kwargs.pop('owner', None)
        if self.owner is None:
            raise ValueError("required parameter: owner")

        super().__init__(*args, **kwargs)

        main_layout = qtw.QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.back_button = qtw.QPushButton("Back")
        self.back_button.setStyleSheet(STYLE_LARGE_BUTTON)
        self.back_button.clicked.connect(self.owner.workflow.navigate_prev)

        self.continue_button = qtw.QPushButton("Continue")
        self.continue_button.setStyleSheet(STYLE_LARGE_BUTTON)
        self.continue_button.clicked.connect(self.owner.workflow.navigate_next)

        main_layout.addWidget(self.back_button)
        main_layout.addStretch()
        main_layout.addWidget(self.continue_button)

        self.setLayout(main_layout)
    #}}}

class LinkedWidget:
    #{{{
    def __init__(self, *args, **kwargs):
        #logger.debug(f"{self.__class__.__name__}.__init__()")
 
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
        self.setObjectName(__class__.__name__)       

    @property
    def page_state(self):
        return self.owner.page_state

    @property
    def workflow_state(self):
        return self.owner.workflow_state


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

class ZCheckBox(qtw.QCheckBox, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.toggled.connect(self.handle_changed)

    def handle_changed(self, status):
        self.page_state[self.page_state_key] = status
        self.owner.update()

    def restore_state(self):
        super().restore_state()
        status = self.page_state.setdefault(self.page_state_key, False)
        self.setChecked(status)
    #}}}

class ZDateTimeEdit(qtw.QDateTimeEdit, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.setCalendarPopup(True)
        self.dateTimeChanged.connect(self.handle_changed)

    def handle_changed(self):
        self.page_state[self.page_state_key] = self.dateTime().toString(qtc.Qt.DateFormat.ISODate)
        self.owner.update()

    def restore_state(self):
        super().restore_state()
        now = qtc.QDateTime.currentDateTime().toString(qtc.Qt.DateFormat.ISODate)

        datetime = self.page_state.setdefault(self.page_state_key, now)

        self.setDateTime(
            qtc.QDateTime.fromString(datetime, qtc.Qt.DateFormat.ISODate)
        )
    #}}}

class ZLabel(qtw.QLabel, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setText(self, txt):
        self.page_state[self.page_state_key] = txt
        super().setText(txt)
        #self.owner.update()

    def restore_state(self):
        super().restore_state()

        if self.page_state_key.startswith('attr:'):
            attr_key = self.page_state_key[5:]
            if hasattr(self.owner, attr_key):
                txt = getattr(self.owner, attr_key) or self.default_value
            else:
                txt = self.default_value
        else:
            txt = self.page_state.get(self.page_state_key, self.default_value)
        super().setText(txt)

    #}}}

class ZLineEdit(qtw.QLineEdit, LinkedWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textChanged.connect(self.handle_changed)
    
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
        super().__init__(*args, **kwargs)

        self._changed = False
        self.setTabChangesFocus(True)
        self.textChanged.connect(self._handle_text_changed)

        self.textChanged.connect(self.handle_editingFinished)

    def handle_editingFinished(self):
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
        super().__init__(*args, **kwargs)
        self.toggled.connect(self.handle_selected)

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
        super().__init__(*args, **kwargs)
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
        self.page_state[self.page_state_key] = self.filename_lineedit.text()
        self.owner.update()

    def restore_state(self):
        super().restore_state()
        self.filename_lineedit.setText(self.page_state.get(self.page_state_key, ''))
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
        self.page_state[self.page_state_key] = str(self.institution_id)
        self.owner.update()

    def restore_state(self):
        self.country_widget.blockSignals(True)
        self.inst_widget.blockSignals(True)
        
        self.institution_id = str(self.page_state.setdefault(
                                            self.page_state_key, self.default_value))
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

