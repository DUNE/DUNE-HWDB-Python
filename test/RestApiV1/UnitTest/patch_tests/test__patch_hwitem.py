#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Authors:
    Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy

Tests updating an item
"""

from Sisyphus.Configuration import config
logger = config.getLogger()
from Sisyphus.Utils import UnitTest as unittest

import os
import json
import random
import time
from datetime import datetime

from Sisyphus.RestApiV1 import post_hwitem
from Sisyphus.RestApiV1 import patch_hwitem
from Sisyphus.RestApiV1 import get_hwitem
from Sisyphus.RestApiV1 import patch_hwitem_subcomp
from Sisyphus.RestApiV1 import patch_hwitem_status
from Sisyphus.RestApiV1 import patch_hwitem_enable

class Test__patch_hwitem(unittest.TestCase):
    """Tests updating an item"""
     
    def setUp(self):
        self.start_time = time.time()
        print(f"\nTest #{getattr(self, 'test_number', 'N/A')}: {self.__class__.__name__}.{self._testMethodName}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def tearDown(self):
        end_time = time.time()
        duration = end_time - self.start_time
        print(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test duration: {duration:.2f} seconds")
    
    def test_patch_hwitem(self):
        print("\n=== Testing to create and update an Item ===")
        print("PATCH /api/v1/components/{part_id}")

        # Part 1, post a component
        part_type_id = "Z00100300001"
        serial_number = f"SN{random.randint(0, 999999):06d}"

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
                "Comment": "Unit Test: patch component, part 1"
            },
            "subcomponents": {},
            #"enabled": True,
        }

        logger.info(f"Posting new hwitem: part_type_id={part_type_id}, serial_number={serial_number}")
        resp = post_hwitem(part_type_id, data)
        logger.info(f"Response from post: {resp}") 
        self.assertEqual(resp["status"], "OK")

        component_id = resp["component_id"]
        part_id = resp["part_id"]

        print(f"A new PID, {part_id}, has been created")

        # Part 2, patch it
        new_serial_number = f"SN{random.randint(0x00000000, 0xFFFFFFFF):08X}"
        
        logger.info(f"Attempting to patch hwitem: part_id={part_id}, serial_number={new_serial_number}")

        data = {
            "comments": "this component has been patched",
            "manufacturer": {
                "id": 7
            },
            "part_id": part_id,
            "serial_number": new_serial_number,
            "specifications": {
                "Widget ID": new_serial_number,
                "Color": "green",
                "Comment": "Unit Test: patch component, part 2"
            },
        }

        resp = patch_hwitem(part_id, data)
        logger.info(f"Response from patch: {resp}")
        self.assertEqual(resp["status"], "OK")

        print(f"The item with PID {part_id} has been updated with new serial number {new_serial_number}")

        # Part 3, get it and check that the data has been updated
        logger.info(f"getting hwitem for comparison: part_id={part_id}")
        
        resp = get_hwitem(part_id)

        logger.info(f"result: {resp}")
        
        self.assertEqual(resp["status"], "OK")
        self.assertEqual(resp["data"]["part_id"], part_id)
        self.assertEqual(resp["data"]["serial_number"], serial_number)
        self.assertEqual(resp["data"]["enabled"], False)
        self.assertDictEqual(resp["data"]["specifications"][0], data["specifications"])

        print(f"The updated item specifications: {json.dumps(resp['data']['specifications'][0], indent=2)}")

    def test_patch_hwitem_subcomp(self):
        print("\n=== Testing to create a new sub-component link ===")
        print("PATCH /api/v1/components/{part_id}/subcomponents")

        # Posting new item under Test Type 002
        part_type_id = "Z00100300002"
        serial_number = f"SN{random.randint(0, 999999):06d}"

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
            "subcomponents": {},
            "status": {
                "id": 1
            }
        }

        resp = post_hwitem(part_type_id, data)
        logger.info(f"Response from post: {resp}") 
        self.assertEqual(resp["status"], "OK")

        part_id_subcomp = resp["part_id"]
        print(f"A new sub-component PID, {part_id_subcomp}, has been created")

        #patching to enable : True
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
        print(f"The sub-component PID, {part_id_subcomp}, has been enabled")

        # Linking subcomponent to container
        part_id_container = "Z00100300001-00360"

        data = {
            "component": {
                "part_id": part_id_container
            },
            "subcomponents": {
                "Subcomp 1" : part_id_subcomp,
            }
        }

        resp = patch_hwitem_subcomp(part_id_container, data)
        logger.info(f"Response from patch: {resp}")
        self.assertEqual(resp["status"], "OK")
        print(f"The sub-component PID, {part_id_subcomp}, has been linked to container PID, {part_id_container}")
        
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
        print(f"The sub-component PID, {part_id_subcomp}, has been removed from container PID, {part_id_container}")
            
if __name__ == "__main__":
    unittest.main(argv=config.remaining_args)
