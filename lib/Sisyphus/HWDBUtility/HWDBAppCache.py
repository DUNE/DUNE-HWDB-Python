#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy

Allows storing and retrieving settings, configuration, and other 
application-level data for component types and HW items. 

Data is stored in a test named "_meta" for a given component type. For
data applicable to the component type in general, data is stored in the
test type definition. For data specific to an individual item, it is 
stored in tests of that test type for the item itself.
"""
from Sisyphus.Utils import utils
from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut
import json 
from copy import deepcopy

APP_DATA = "APPLICATION_DATA"

class HWItemCache:
    def __init(self, part_id):
        raise NotImplementedError("Coming soon! Or... eventually? Maybe?")

class ComponentTypeCache:
    _existing_caches = {}

    def __init__(self, part_type_id=None, part_type_name=None):
        #{{{
        # Look up component type and resolve id/name
        # (don't worry, the 'fetch' uses a cache of its own!)
        self._ct_data = ut.fetch_component_type(part_type_id, part_type_name)
        self.part_type_id = self._ct_data["ComponentType"]["part_type_id"]
        self.part_type_name = self._ct_data["ComponentType"]["full_name"]

        # If we've already created this, return the one we created
        if self.part_type_id in self._existing_caches:
            return self._existing_caches[self.part_type_id]

        self.fetch()
        #}}}

    def fetch(self):
        #{{{
        if "_meta" in self._ct_data["TestTypeDefs"]:
            self._latest_db_cache = deepcopy(self._ct_data["TestTypeDefs"]["_meta"]["data"]
                            ["properties"]["specifications"][-1]["datasheet"])
            utils.restore_order(self._latest_db_cache)
            self._current_cache = deepcopy(self._latest_db_cache)
        else:
            self._latest_db_cache = None  # Interpret this as "not created yet"
            self._current_cache = {}

        if APP_DATA not in self._current_cache:
            self._current_cache[APP_DATA] = {}
        #}}}

    def has_changed(self):
        #{{{
        # Re-establish the correct order before comparing
        utils.preserve_order(self._latest_db_cache)
        utils.preserve_order(self._current_cache)
        return self._latest_db_cache != self._current_cache
        #}}}

    def commit(self):
        #{{{
        if not self.has_changed():
            print("no change. won't update.")
            return

        if self._latest_db_cache is None:
            print("creating a new one")
            # Does not exist yet. We need to create it.
            req_data = \
            {
                "comments": "For HWDB application use only. Storage for "
                            "application-specific data pertaining to this "
                            "Component Type or HW Item.",
                "component_type": {"part_type_id": self.part_type_id},
                "name": "_meta",
                "specifications": self._current_cache
            }
            print(json.dumps(req_data, indent=4)) 
            resp = ra.post_test_type(self.part_type_id, req_data)
            print(resp)
        else:
            print("updating existing one")
            req_data = \
            {
                "comments": "For HWDB application use only. Storage for "
                            "application-specific data pertaining to this "
                            "Component Type or HW Item.",
                "component_type": {"part_type_id": self.part_type_id},
                "name": "_meta",
                "specifications": self._current_cache
            }
            print(json.dumps(req_data, indent=4))
            resp = ra.post_test_type(self.part_type_id, req_data)
            print(resp)

        self._latest_db_cache = self._current_cache


        #}}}


    #{{{ all the "dictionary" methods
    def __getitem__(self, key):
        return self._current_cache[APP_DATA][key]

    def __setitem__(self, key, value):
        self._current_cache[APP_DATA][key] = value

    def __delitem__(self, key):
        del self._current_cache[APP_DATA][key]

    def __contains__(self, item):
        return item in self._current_cache[APP_DATA]

    def keys(self):
        return self._current_cache[APP_DATA].keys()

    def values(self):
        return self._current_cache[APP_DATA].values()

    def items(self):
        return self._current_cache[APP_DATA].items()

    def get(self, *args, **kwargs):
        return self._current_cache[APP_DATA].get(*args, **kwargs)

    def clear(self):
        return self._current_cache[APP_DATA].clear()

    def setdefault(self, *args, **kwargs):
        return self._current_cache[APP_DATA].setdefault(*args, **kwargs)

    def pop(self, *args, **kwargs):
        return self._current_cache[APP_DATA].pop(*args, **kwargs)
    
    def popitem(self, *args, **kwargs):
        return self._current_cache[APP_DATA].popitem(*args, **kwargs)

    def copy(self, *args, **kwargs):
        return self._current_cache[APP_DATA].copy(*args, **kwargs)
    
    def update(self, *args, **kwargs):
        return self._current_cache[APP_DATA].update(*args, **kwargs)
    #}}}
































