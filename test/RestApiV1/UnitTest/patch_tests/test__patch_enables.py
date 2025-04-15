#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy

Tests setting "enabled" status in item
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)
from Sisyphus.Utils import UnitTest as unittest

import os
import json
import unittest
import random
import time
from datetime import datetime

from Sisyphus.RestApiV1 import post_hwitem
from Sisyphus.RestApiV1 import patch_hwitem
from Sisyphus.RestApiV1 import get_hwitem
from Sisyphus.RestApiV1 import patch_hwitem_enable
from Sisyphus.RestApiV1 import patch_hwitem_status
from Sisyphus.RestApiV1 import post_hwitems_bulk
from Sisyphus.RestApiV1 import patch_hwitems_enable_bulk

class Test__patch_enables(unittest.TestCase):
    """Tests setting "enabled" status in item"""
    
    def setUp(self):
        self.start_time = time.time()
        print(f"\nTest #{getattr(self, 'test_number', 'N/A')}: {self.__class__.__name__}.{self._testMethodName}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def tearDown(self):
        end_time = time.time()
        duration = end_time - self.start_time
        print(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test duration: {duration:.2f} seconds")
    
    def test__patch_hwitem_enable(self):
        print("\n=== Testing to create an Item and toggle its enabled status ===")
        print("PATCH /api/v1/components/{part_id}/enable")

        # POST
        part_type_id = "Z00100300001"
        serial_number = "S99999"

        data = {
            "comments": "Here are some comments",
            "component_type": {
                "part_type_id": part_type_id
            },
            "country_code": "US",
            "institution": {
                "id": 186
            },
            "manufacturer": {
                "id": 7
            },
            "serial_number": serial_number,
            "specifications": {
                "Widget ID": serial_number,
                "Color": "red",
                "Comment": "Unit Testing"
            },
            "subcomponents": {},
            "status": {
                "id": 1
            }
        }

        logger.info(f"Posting new hwitem: part_type_id={part_type_id}, serial_number={serial_number}")
        resp = post_hwitem(part_type_id, data)
        logger.info(f"Response from post: {resp}") 
        self.assertEqual(resp["status"], "OK")

        component_id = resp["component_id"]
        part_id = resp["part_id"]

        print(f"A new PID, {part_id}, has been created")

        # PATCH ENABLE
        data = {
            "comments": "here are some comments",
            "component": {
            "id": component_id,
            "part_id": part_id
            },
            "enabled": True,
            "geo_loc": {
            "id": 0
            }
        }

        resp = patch_hwitem_enable(part_id, data)
        logger.info(f"Response from patch: {resp}")
        self.assertEqual(resp["status"], "OK")

        # GET/CHECK
        resp = get_hwitem(part_id)
        self.assertTrue(resp["data"]["enabled"])

        # PATCH DISABLE
        data["enabled"] = False
        resp = patch_hwitem_enable(part_id, data)
        logger.info(f"Response from patch: {resp}")
        self.assertEqual(resp["status"], "OK")

        # GET/CHECK
        resp = get_hwitem(part_id)
        self.assertFalse(resp["data"]["enabled"])

        #}}}

    #-------------------------------------------------------------------------

    #post (2) items in bulk, get part ids from response of post, 
    # use those part ids to enable them, check if they were enabled. 
    # Disable them, check if they were disabled
    def test_patch_enable_bulk(self):
        """Tests setting "enabled" status in several items at the same time"""

        # POST bulk
        part_type_id = "Z00100300001"
        data = {
            "comments": "Here are some comments",
            "component_type": {
                "part_type_id": part_type_id
            },
            "count": 2,
            "country_code": "US",
            "institution": {
            "id": 186
            },
            "manufacturer": {
                "id": 7
            }
        }

        logger.info(f"Posting bulk components: part_type_id={part_type_id}")
        resp = post_hwitems_bulk(part_type_id, data)
        logger.info(f"Response from post: {resp}") 
        self.assertEqual(resp["status"], "OK")

        part_id1 = resp["data"][0]["part_id"]
        part_id2 = resp["data"][1]["part_id"]

        print(f"Two new PIDs have been created: {part_id1} and {part_id2}")

        # ENABLE
        data = {
            "data": [{
                "comments": "string",
                "enabled": True,
                "part_id": part_id1
                },
                {
                "comments": "string",
                "enabled": True,
                "part_id": part_id2
                }
            ]}
        
        resp = patch_hwitems_enable_bulk(data)
        logger.info(f"Response from patch: {resp}")
        
        # GET/CHECK
        resp = get_hwitem(part_id1)
        resp2 = get_hwitem(part_id2)
        self.assertTrue(resp["data"]["enabled"])
        self.assertTrue(resp2["data"]["enabled"])
        logger.info(f"Response from post: {resp}") 

        # DISABLE
        data = {
            "data": [{
                "comments": "string",
                "enabled": False,
                "part_id": part_id1
                },
                {
                "comments": "string",
                "enabled": False,
                "part_id": part_id2
                }
            ]}
        
        resp = patch_hwitems_enable_bulk(data)
        logger.info(f"Response from patch: {resp}")

        # GET/CHECK
        resp = get_hwitem(part_id1)
        resp2 = get_hwitem(part_id2)
        self.assertFalse(resp["data"]["enabled"])
        self.assertFalse(resp2["data"]["enabled"])
        logger.info(f"Response from post: {resp}")

#=================================================================================

if __name__ == "__main__":
    unittest.main(argv=config.remaining_args)