#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Authors:
    Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy

Test POST methods in RestApiV1
"""

from Sisyphus.Configuration import config
logger = config.getLogger()
from Sisyphus.Utils import UnitTest as unittest

import os
import json
import unittest
import random
import time
from datetime import datetime

import Sisyphus.RestApiV1 as ra
from Sisyphus.RestApiV1 import post_test_type, post_test

class Test__post_tests(unittest.TestCase):
    """Test POST methods in RestApiV1"""
    
    def setUp(self):
        self.start_time = time.time()
        print(f"\nTest #{getattr(self, 'test_number', 'N/A')}: {self.__class__.__name__}.{self._testMethodName}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def tearDown(self):
        end_time = time.time()
        duration = end_time - self.start_time
        print(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test duration: {duration:.2f} seconds")
    
    @unittest.skip("adds too much data to be run daily")
    def test_post_test_type(self):
        print("\n=== Testing to post a new test type ===")
        print("Endpoint used: POST /test_type")

        part_type_id = "Z00100300001"

        data = {
                "comments": "adding new test",
                "component_type": {
                    "part_type_id": part_type_id
                },
                "name": "unittest2",
                "specifications": {"Speed": ["slow", "medium", "fast"]}
                }
        
        resp = post_test_type(part_type_id, data)
        logger.info(f"Response from post: {resp}") 
        self.assertEqual(resp["status"], "OK")
        print(f"A new test type 'unittest2' has been created for part_type_id {part_type_id}")

    def test_post_test_good(self):
        print("\n=== Testing to post a test with valid data ===")
        print("POST /api/v1/components/{part_id}/tests")

        part_id = "Z00100300001-00360"

        data = {        
            "comments": "posting good test for unit test",
            "test_data": {
                "Any": "slow",
                "Color": "Yellow",
                "Flavor": "vanilla"
            },
            "test_type": "unittest1"
        }
        
        resp = post_test(part_id, data)
        logger.info(f"Response from post: {resp}")
        self.assertEqual(resp["status"], "OK")
        print(f"A new test of type 'unittest1' has been successfully posted for part_id {part_id}")

    def test_post_test_missing(self):
        print("\n=== Testing to post a test with missing data ===")
        print("POST /api/v1/components/{part_id}/tests")

        part_id = "Z00100300001-00360"

        data = {
            "comments": "posting test for unit test",
            "test_data": {
                "Any": "slow",
                # Missing "Color" field from definition
                "Flavor": "vanilla"
            },
            "test_type": "unittest1"
        }
      
        with self.assertRaises(ra.exceptions.BadSpecificationFormat): 
            logger.warning("NOTE: The following subtest raises an exception. This is normal.")
            resp = post_test(part_id, data)
            logger.info(f"Response from post: {resp}")
        print(f"Test passed: BadSpecificationFormat exception raised as expected for part_id {part_id}")

    def test_post_test_bad(self):
        print("\n=== Testing to post a test with an invalid selection ===")
        print("POST /api/v1/components/{part_id}/tests")

        part_id = "Z00100300001-00360"

        data = {
            "comments": "posting test for unit test",
            "test_data": {
                "Any": "slow",
                "Color": "Green",
                "Flavor": "blueberry" # Not an option in the definition
            },
            "test_type": "unittest1"
        }
      
        with self.assertRaises(ra.exceptions.BadSpecificationFormat): 
            logger.warning("NOTE: The following subtest raises an exception. This is normal.")
            resp = post_test(part_id, data)
            logger.info(f"Response from post: {resp}")
        print(f"Test passed: BadSpecificationFormat exception raised as expected for part_id {part_id}")

    def test_post_test_extra(self):
        print("\n=== Testing to post a test with extra data ===")
        print("POST /api/v1/components/{part_id}/tests")

        part_id = "Z00100300001-00360"

        data = {
            "comments": "posting test for unit test",
            "test_data": {
                "Any": "slow",
                "Color": "Yellow",
                "Flavor": "vanilla",
                "_meta": {},
            },
            "test_type": "unittest1"
        }
      
        resp = post_test(part_id, data)
        logger.info(f"Response from post: {resp}")
        self.assertEqual(resp["status"], "OK")
        print(f"A new test of type 'unittest1' with extra data has been successfully posted for part_id {part_id}")

if __name__ == "__main__":
    unittest.main(argv=config.remaining_args)