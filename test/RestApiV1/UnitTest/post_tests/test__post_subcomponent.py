#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Authors:
    Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy

Tests adding subcomponents to an item
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
from Sisyphus.RestApiV1 import patch_hwitem_enable
from Sisyphus.RestApiV1 import patch_hwitem_subcomp

class Test__post_subcomponent(unittest.TestCase):
    """Tests adding subcomponents to an item"""
    
    def setUp(self):
        self.start_time = time.time()
        print(f"\nTest #{getattr(self, 'test_number', 'N/A')}: {self.__class__.__name__}.{self._testMethodName}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def tearDown(self):
        end_time = time.time()
        duration = end_time - self.start_time
        print(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test duration: {duration:.2f} seconds")
    
    def test_post_subcomponent(self):
        print("\n=== Testing to add subcomponents to an Item ===")
        print("POST /api/v1/component-types/{part_type_id}/components")


        # Posting new item under Test Type 002
        part_type_id = "Z00100300002"
        serial_number = "S99999"

        data = {
            "comments": "posting for sub comp",
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
                    "Color":"Red"
            },
            "subcomponents": {}
        }

        resp = post_hwitem(part_type_id, data)
        logger.info(f"Response from post: {resp}") 
        self.assertEqual(resp["status"], "OK")

        part_id_subcomp = resp["part_id"]
        print(f"A new subcomponent Item with part_id {part_id_subcomp} has been created")

        data = {
            "comments": "here are some comments",
            "component": {
            "part_id": part_id_subcomp
            },
            "enabled": True,
            "geo_loc": {
            "id": 0
            }
        }

        resp = patch_hwitem_enable(part_id_subcomp, data)
        logger.info(f"Response from patch: {resp}")
        self.assertEqual(resp["status"], "OK")
        print(f"The subcomponent Item with part_id {part_id_subcomp} has been enabled")

        # Posting hwitem with subcomponent
        part_type_id = "Z00100300001"
        serial_number = f"SN{random.randint(0x00000000, 0xFFFFFFFF):08X}"
        data = {
            "comments": "unit testing",
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
            "specifications": 
            {
                "Widget ID": serial_number,
                "Color": "red",
                "Comment": "Unit Test: post component with subcomponent"
            },
            "subcomponents": {"Subcomp 1" : part_id_subcomp}
        }
        resp = post_hwitem(part_type_id, data)
        logger.info(f"response was {resp}")
        self.assertEqual(resp["status"], "OK")

        part_id_container = resp["part_id"]
        print(f"A new container Item with part_id {part_id_container} has been created with subcomponent {part_id_subcomp}")

        # Removing subcomponent from container
        data = {
            "component": {
                "part_id": part_id_container
            },
            "subcomponents": {
                "Subcomp 1": None,
            }
        }

        resp = patch_hwitem_subcomp(part_id_container, data)
        logger.info(f"Response from patch: {resp}")
        self.assertEqual(resp["status"], "OK")
        print(f"The subcomponent {part_id_subcomp} has been removed from the container Item {part_id_container}")

if __name__ == "__main__":
    unittest.main(argv=config.remaining_args)