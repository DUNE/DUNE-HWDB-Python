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

from Sisyphus.RestApiV1 import get_test_type, get_hwitem_test
from Sisyphus.RestApiV1 import get_test_types
from Sisyphus.RestApiV1 import get_test_type_by_oid

class Test__get_tests(unittest.TestCase):
    """Test RestApi functions related to Item Tests"""
    
    def setUp(self):
        self.start_time = time.time()
        #print(f"\nTest #{getattr(self, 'test_number', 'N/A')}: {self.__class__.__name__}.{self._testMethodName}")
        #print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def tearDown(self):
        end_time = time.time()
        duration = end_time - self.start_time
        #print(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        #print(f"Test duration: {duration:.2f} seconds")
    
    def setUp(self):
        self.start_time = time.time()
        #print("\n")
        #print(f"\nTest started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def tearDown(self):
        end_time = time.time()
        duration = end_time - self.start_time
        #print(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        #print(f"Test duration: {duration:.2f} seconds")

    def test_test_types(self):
        """Get a list of test types for a component type"""
        #print("\n=== Testing to get a list of test types for a component type ===")
        #print("GET /api/v1/component-types/{part_type_id}/test-types")
        #print("Retrieving test types for part_type_id: Z00100300001")

        part_type_id = 'Z00100300001'

        self.test_info["endpoint"] = f"GET : /component-types/{part_type_id}/test-types"
        self.test_info["description"] = "Get a list of Test Type Names for a given Component Type"
        self.test_info["check"] = "if status=OK and see if the last Test Type Name is Bounce"

        try:
            resp = get_test_types(part_type_id)            

            self.assertEqual(resp['status'], "OK")
            self.assertEqual(resp["data"][-1]["name"], "Bounce")
        
        except Exception as e:
            # Try to get raw server response if available
            api_resp = getattr(e, "response", None)

            if api_resp is not None:
                # If the API wrapper supports .json(), use it
                try:
                    self.test_info["error"] = json.dumps(api_resp.json(), indent=4)
                except Exception:
                    # Fallback: raw string body
                    self.test_info["error"] = api_resp.text
            else:
                # Nothing from server, probably client-side issue
                self.test_info["error"] = str(e)

            # Preserve traceback for summary
            logger.error(f"Exception: {repr(e)}")
            raise
        
    def test_test_type(self):
        """Get a specific test type definition"""
        #print("\n=== Testing to get a specific test type definition ===")
        #print("GET /api/v1/component-types/{part_type_id}/test-types/{test_type_id}")
        #print("Retrieving test type for part_type_id: Z00100300001, test_type_id: 492")

        part_type_id = 'Z00100300001'
        test_type_id = 492

        self.test_info["endpoint"] = f"GET : /component-types/{part_type_id}/test-types/{test_type_id}"
        self.test_info["description"] = "Get the Test Type definition of type_id = 492"
        self.test_info["check"] = "if status=OK and see if the Test Type Name is Test Type 001 and part_type_id is Z00100300001"

        try:
            resp = get_test_type(part_type_id, test_type_id)            

            self.assertEqual(resp['status'], "OK")
            self.assertEqual(resp["component_type"]["name"], "Test Type 001")
            self.assertEqual(resp["component_type"]["part_type_id"], part_type_id)
        
        except Exception as e:
            # Try to get raw server response if available
            api_resp = getattr(e, "response", None)

            if api_resp is not None:
                # If the API wrapper supports .json(), use it
                try:
                    self.test_info["error"] = json.dumps(api_resp.json(), indent=4)
                except Exception:
                    # Fallback: raw string body
                    self.test_info["error"] = api_resp.text
            else:
                # Nothing from server, probably client-side issue
                self.test_info["error"] = str(e)

            # Preserve traceback for summary
            logger.error(f"Exception: {repr(e)}")
            raise

    def test_test_type_by_oid(self):
        """Get a specific test type definition by oid"""
        #print("\n=== Testing to get a specific test type definition by oid ===")
        #print("GET /api/v1/component-test-types/{oid}")
        #print("Retrieving test type for oid: 1")

        oid = 1

        self.test_info["endpoint"] = f"GET : /component-test-types/{oid}"
        self.test_info["description"] = "Get the Test Type definition of oid = 1"
        self.test_info["check"] = "if status=OK and see if the response matches with the expected one"

        try:
            
            file_path = os.path.join(os.path.dirname(__file__),
                    '..','ExpectedResponses', 'ops_on_tests', 'oid1.json')
            with open(file_path, 'r') as file:
                expected_resp = json.load(file)
            resp = get_test_type_by_oid(oid)            

            self.assertEqual(resp['status'], "OK")
            self.assertDictEqual(resp, expected_resp)

        except Exception as e:
            # Try to get raw server response if available
            api_resp = getattr(e, "response", None)

            if api_resp is not None:
                # If the API wrapper supports .json(), use it
                try:
                    self.test_info["error"] = json.dumps(api_resp.json(), indent=4)
                except Exception:
                    # Fallback: raw string body
                    self.test_info["error"] = api_resp.text
            else:
                # Nothing from server, probably client-side issue
                self.test_info["error"] = str(e)

            # Preserve traceback for summary
            logger.error(f"Exception: {repr(e)}")
            raise

    def test_test_hwitem(self):
        """Get a specific test data from a specific item"""
        #print("\n=== Testing to get a specific test data from a specific item ===")
        #print("GET /api/v1/components/{part_id}/tests")
        #print("Retrieving test data for part_id: Z00100300001-00360, test_type_name: unittest1")

        part_id = 'Z00100300001-00360'
        test_type_name = 'unittest1'

        self.test_info["endpoint"] = f"GET : /components/{part_id}/tests/{test_type_name}"
        self.test_info["description"] = f"Get the latest test data of Test Type Name = {test_type_name} under PID = {part_id}"
        self.test_info["check"] = "if status=OK"

        try:
            resp = get_hwitem_test(part_id,test_type_name)

            self.assertEqual(resp['status'], "OK")
        
        except Exception as e:
            # Try to get raw server response if available
            api_resp = getattr(e, "response", None)

            if api_resp is not None:
                # If the API wrapper supports .json(), use it
                try:
                    self.test_info["error"] = json.dumps(api_resp.json(), indent=4)
                except Exception:
                    # Fallback: raw string body
                    self.test_info["error"] = api_resp.text
            else:
                # Nothing from server, probably client-side issue
                self.test_info["error"] = str(e)

            # Preserve traceback for summary
            logger.error(f"Exception: {repr(e)}")
            raise

if __name__ == "__main__":
    unittest.main(argv=config.remaining_args)