#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/DataModel/_HWTestType.py
Copyright (c) 2024 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

import Sisyphus.RestApiV1 as ra
import Sisyphus.RestApiV1.Utilities as ut
from Sisyphus.Utils.utils import preserve_order, restore_order, serialize_for_display

from copy import deepcopy
import json

class HWTestType:
   
    _cache = {}

    def __new__(cls, part_type_id=None, part_type_name=None, 
                            test_name=None, use_cache=True, **kwargs):
        if (part_type_id, test_name) in cls._cache:
            #print("returning test type from cache")
            return cls._cache[part_type_id, test_name]
        else:
            #print("creating new test type")
            return super(HWTestType, cls).__new__(cls, part_type_id, part_type_name, 
                            test_name, use_cache, **kwargs)
 
    def __init__(self, part_type_id=None, part_type_name=None, test_name=None, use_cache=True):
        # I hate to have to import this here, but we don't want to
        # have problems with circular references
        from ._HWComponentType import HWComponentType
        
        if (part_type_id, test_name) in cls._cache:
            # __new__ should have already returned the cached type, which
            # has already been constructed, so just return
            #print("returning without initializing")
            return

        resp_data = ut.fetch_component_type(part_type_id, part_type_name, use_cache)
        component_data = resp_data["ComponentType"]
        test_data = resp_data["TestTypeDefs"].get(test_name, {}).get("data", None)


        self._current = data = {
            "part_type_id": component_data["part_type_id"],
            "part_type_name": component_data["full_name"],
            "test_name": test_name,
        }
        
        if test_data is None:
            raise ValueError(f"Test {test_name} not found for {data['part_type_id']}")

        self.component_type = HWComponentType(part_type_id=data['part_type_id'])


        data.update({
            "comments": test_data["comments"],
            "oid": test_data["id"],
            "specifications": restore_order(test_data["properties"]
                                        ["specifications"][-1]["datasheet"]),
        })

        
        #print(json.dumps(data, indent=4))


        self._cache[data['part_type_id'], test_name] = self

