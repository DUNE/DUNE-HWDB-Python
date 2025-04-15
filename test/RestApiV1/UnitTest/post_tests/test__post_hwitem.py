#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Authors:
    Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy

Tests posting an item
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
from Sisyphus import RestApiV1 as ra

class Test__post_hwitem(unittest.TestCase):
    """Tests posting Items"""
    
    def setUp(self):
        self.start_time = time.time()
        print(f"\nTest #{getattr(self, 'test_number', 'N/A')}: {self.__class__.__name__}.{self._testMethodName}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def tearDown(self):
        end_time = time.time()
        duration = end_time - self.start_time
        print(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test duration: {duration:.2f} seconds")
    
    def test__post_hwitem(self):
        print("\n=== Testing to post a new Item ===")
        print("POST /api/v1/component-types/{part_type_id}/components")
 

        part_type_id = "Z00100300001"
        serial_number = f"SN{random.randint(0x00000000, 0xFFFFFFFF):08X}"

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
            "specifications": 
            {
                "Widget ID": serial_number,
                "Color": "red",
                "Comment": "Unit Test: post component"
            },
            "subcomponents": {}
        }

        resp = post_hwitem(part_type_id, data)


        logger.info(f"The response was: {resp}")

        logger.info(f"Created: {resp['part_id']}")
        
        self.assertEqual(resp["status"], "OK")
        
        #}}}
    #-------------------------------------------------------------------------

    #@unittest.skip("fails")
    def test__post_hwitem__empty_spec(self):
        print("\n=== Testing to post a new Item with empty specifications ===")
        print("POST /api/v1/component-types/{part_type_id}/components")

        part_type_id = "Z00100300006"
        serial_number = f"SN{random.randint(0x00000000, 0xFFFFFFFF):08X}"

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
            "specifications": {},
            "subcomponents": {}
        }

        resp = post_hwitem(part_type_id, data)

        logger.info(f"The response was: {resp}")

        self.assertEqual(resp["status"], "OK")
        print(f"A new Item with part_type_id {part_type_id} and empty specifications has been created")

    def test__post_hwitem__bad_spec(self):
        print("\n=== Testing to post a new Item with bad specifications ===")
        print("POST /api/v1/component-types/{part_type_id}/components")
            
        part_type_id = "Z00100300001"
        serial_number = f"SN{random.randint(0x00000000, 0xFFFFFFFF):08X}"

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
            "specifications": 
            {
                "Widget-ID": serial_number, # The key is misspelled
                "Color": "red",
                "Comment": "Unit Test: post component"
            },
            "subcomponents": {}
        }

        with self.assertRaises(ra.BadSpecificationFormat):
            resp = post_hwitem(part_type_id, data)
        print("Test passed: BadSpecificationFormat exception raised as expected")

    def test__post_hwitem__extra_spec(self):
        #{{{
        """Tests posting an item with extra fields in the spec, which should be allowed"""

        part_type_id = "Z00100300001"
        serial_number = f"SN{random.randint(0x00000000, 0xFFFFFFFF):08X}"

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
            "specifications": 
            {
                "Widget ID": serial_number,
                "Color": "red",
                "Comment": "Unit Test: post component",
                "Extra": 3
            },
            "subcomponents": {}
        }

        with self.assertRaises(ra.BadSpecificationFormat):
            resp = post_hwitem(part_type_id, data)

        #logger.info(f"The response was: {resp}")
        
        self.assertEqual(resp["status"], "OK")
        #}}}

    #-------------------------------------------------------------------------

    def test__post_hwitem__sparse(self):
        print("\n=== Testing to post a new Item with missing optional data ===")
        print("POST /api/v1/component-types/{part_type_id}/components")

        part_type_id = "Z00100300001"
        serial_number = f"SN{random.randint(0x00000000, 0xFFFFFFFF):08X}"

        data = {
            "component_type": {
                "part_type_id": part_type_id
            },
            "country_code": "US",
            "institution": {
                "id": 186
            },
            "specifications":
            {
                "Widget ID": serial_number,
                "Color": "red",
                "Comment": "Unit Test: post component",
            },
        }

        resp = post_hwitem(part_type_id, data)

        logger.info(f"The response was: {resp}")

        self.assertEqual(resp["status"], "OK")
        print(f"A new Item with part_type_id {part_type_id} and missing optional data has been created")

    def test__post_hwitem__bad_fields(self):
        print("\n=== Testing to post a new Item with missing and extra fields ===")
        print("POST /api/v1/component-types/{part_type_id}/components")

        part_type_id = "Z00100300001"
        serial_number = f"SN{random.randint(0x00000000, 0xFFFFFFFF):08X}"

        data = {
            "component_type": {
                "part_type_id": part_type_id
            },
            "bad_field": "abc",
            "institution": 186,
            "specifications":
            {
                "Widget ID": serial_number,
                "Color": "red",
                "Comment": "Unit Test: post component",
            },
        }

        with self.assertRaises(ra.BadDataFormat):
            resp = post_hwitem(part_type_id, data)
        print("Test passed: BadDataFormat exception raised as expected")

if __name__ == "__main__":
    unittest.main(argv=config.remaining_args)

