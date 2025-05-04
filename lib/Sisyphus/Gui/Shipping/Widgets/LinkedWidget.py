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

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtGui as qtg

###############################################################################

STYLE_LARGE_BUTTON = """
    font-size: 15pt;
    padding: 5px 15px;
"""

STYLE_SMALL_BUTTON = """
    padding: 5px 15px;
"""

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
        self.default_value = kwargs.pop('default', None)

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
        #{{{
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
        #}}}
    @property
    def page_state(self):
        return self.page.page_state

    @property
    def workflow_state(self):
        return self.page.workflow_state

    @property
    def application_state(self):
        return self.page.application_state

    @property
    def stored_value(self):
        return self.page_state.setdefault(self.state_key, None)

    @stored_value.setter
    def stored_value(self, value):
        self.page_state[self.state_key] = value


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
        #logger.debug(f"{self.__class__.__name__}.restore_state()")
        pass
    #}}}
