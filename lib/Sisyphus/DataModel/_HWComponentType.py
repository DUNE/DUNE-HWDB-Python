#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/DataModel/_HWComponentType.py
Copyright (c) 2024 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.Utils.utils import preserve_order, restore_order, serialize_for_display

import Sisyphus.RestApiV1 as ra
import Sisyphus.RestApiV1.Utilities as ut

from ._HWMisc import Manufacturer, Role

from copy import deepcopy
import json

class HWComponentType:

    _cache = {}

    def __new__(cls, part_type_id=None, *args, **kwargs):
        if part_type_id in cls._cache:
            #print("returning component type from cache")
            return cls._cache[part_type_id] 
        else:
            #print("creating new component type")
            #print(f"cache was: {cls._cache}")
            return super(HWComponentType, cls).__new__(cls, *args, **kwargs)


    def __init__(self, part_type_id=None, part_type_name=None, use_cache=True):
        # I hate to have to import this here, but we don't want to
        # have problems with circular references
        from ._HWTestType import HWTestType
        
        if part_type_id in self._cache:
            # __new__ should have already returned the cached type, which
            # has already been constructed, so just return
            #print("returning without initializing")
            return        
        
        
        resp_data = ut.fetch_component_type(part_type_id, part_type_name, use_cache)
        
        component_data = resp_data["ComponentType"]

        self._current = data = {
            "part_type_id": component_data["part_type_id"],
            "part_type_name": component_data["full_name"],
            "comments": component_data["comments"],
            "connectors": component_data["connectors"],
            "manufacturers": [Manufacturer.make(**s) for s in component_data["manufacturers"]],
            "specifications": restore_order(component_data["properties"]
                                                ["specifications"][-1]["datasheet"]),
            "roles": [Role.make(**s) for s in component_data["roles"]],
            "test_types": {},
        }
        
        # We should cache this now, because when we initialize test types, it's
        # going to try to create a reference back to this, and we don't want an
        # endless loop
        self._cache[data['part_type_id']] = self

        test_type_data = resp_data["TestTypeDefs"]
        for k in test_type_data.keys():
            data["test_types"][k] = HWTestType(
                                        part_type_id=component_data["part_type_id"],
                                        test_name=k)
       
        self.item_encoders = {}
 
        #print(json.dumps(serialize_for_display(data), indent=4))


    @property
    def comments(self):
        return self._current["comments"]

    @property
    def connectors(self):
        return self._current['connectors']

    @property
    def part_type_name(self):
        return self._current['part_type_name']
    @property
    def part_type_name(self):
        return self._current['part_type_id']

    @property
    def manufacturers(self):
        return self._current['manufacturers']

    @property
    def specifications(self):
        return self._current['specifications']

    @property
    def roles(self):
        return self._current['roles']

    @property
    def test_types(self):
        ...

    # TODO
    # project, system, subsystem



