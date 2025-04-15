#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Authors:
    Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy

Test RestApi functions related to Item Tests
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)
from Sisyphus.Utils import UnitTest as unittest

import unittest
import os
import json
import time
from datetime import datetime

from Sisyphus.RestApiV1 import get_test_type
from Sisyphus.RestApiV1 import get_test_types
from Sisyphus.RestApiV1 import get_test_type_by_oid

class Test__get_tests(unittest.TestCase):
    """Test RestApi functions related to Item Tests"""
    
    def setUp(self):
        self.start_time = time.time()
        print(f"\nTest #{getattr(self, 'test_number', 'N/A')}: {self.__class__.__name__}.{self._testMethodName}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def tearDown(self):
        end_time = time.time()
        duration = end_time - self.start_time
        print(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test duration: {duration:.2f} seconds")
    
    def setUp(self):
        self.start_time = time.time()
        print("\n")
        print(f"\nTest started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def tearDown(self):
        end_time = time.time()
        duration = end_time - self.start_time
        print(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test duration: {duration:.2f} seconds")

    def test_test_types(self):
        """Get a list of test types for a component type"""
        print("\n=== Testing to get a list of test types for a component type ===")
        print("GET /api/v1/component-types/{part_type_id}/test-types")
        print("Retrieving test types for part_type_id: Z00100300001")

        try:
            part_type_id = 'Z00100300001'
            
            resp = get_test_types(part_type_id)            

            self.assertEqual(resp['status'], "OK")
            self.assertEqual(resp["data"][-1]["name"], "Bounce")
        
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err

    def test_test_type(self):
        """Get a specific test type definition"""
        print("\n=== Testing to get a specific test type definition ===")
        print("GET /api/v1/component-types/{part_type_id}/test-types/{test_type_id}")
        print("Retrieving test type for part_type_id: Z00100300001, test_type_id: 492")

        try:
            part_type_id = 'Z00100300001'
            test_type_id = 492
            
            resp = get_test_type(part_type_id, test_type_id)            

            self.assertEqual(resp['status'], "OK")
            self.assertEqual(resp["component_type"]["name"], "Test Type 001")
            self.assertEqual(resp["component_type"]["part_type_id"], part_type_id)
        
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err

    def test_test_type_by_oid(self):
        """Get a specific test type definition by oid"""
        print("\n=== Testing to get a specific test type definition by oid ===")
        print("GET /api/v1/component-test-types/{oid}")
        print("Retrieving test type for oid: 1")

        try:
            oid = 1
            file_path = os.path.join(os.path.dirname(__file__),
                    '..','ExpectedResponses', 'ops_on_tests', 'oid1.json')
            with open(file_path, 'r') as file:
                expected_resp = json.load(file)
            resp = get_test_type_by_oid(oid)            

            self.assertEqual(resp['status'], "OK")
            self.assertDictEqual(resp, expected_resp)

        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err

if __name__ == "__main__":
    unittest.main(argv=config.remaining_args)