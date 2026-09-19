#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Authors: 
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
    Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy

Test RestApiV1 functions related to Items
"""

#from Sisyphus.Configuration import config
#logger = config.getLogger()

import os
import json
import unittest
import time
from datetime import datetime

from Sisyphus.Utils import UnitTest as unittest
from Sisyphus.RestApiV1 import get_hwitem
from Sisyphus import RestApiV1 as ra

class Test__get_hwitems(unittest.TestCase):
    """Test RestApiV1 functions related to Items"""
    
    def setUp(self):
        self.start_time = time.time()
        #print(f"\nTest #{getattr(self, 'test_number', 'N/A')}: {self.__class__.__name__}.{self._testMethodName}")
        #print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def tearDown(self):
        end_time = time.time()
        duration = end_time - self.start_time
        #print(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        #print(f"Test duration: {duration:.2f} seconds")
    
    def test_normal_item(self):
        """Get an item"""
        #print("\n=== Testing to get an item ===")
        #print("GET /api/v1/components/{part_id}")
        #print("Retrieving item with part_id: Z00100300001-00021")

        #try:
            #file_path = os.path.join(os.path.dirname(__file__), '..','ExpectedResponses', 
            #                        'components', 'normal_item.json')
            #with open(file_path, 'r') as file:
            #    expected_resp = json.load(file)

        self.test_info["endpoint"] = f"GET : /components/Z00100300001-00021"
        self.test_info["description"] = "Get an item info"
        self.test_info["check"] = "if status=OK and see \"component_id\" is indeed 44801 and \"part_type_id\" is Z00100300001"

        try:
            resp = get_hwitem("Z00100300001-00021")
            self.logger.info(f"Response from post: {resp}")
        
            self.assertEqual(resp["status"], "OK")
            self.assertEqual(resp['data']['component_id'],44801)
            self.assertEqual(resp['data']['component_type']['part_type_id'], 'Z00100300001')
            #self.assertEqual(resp, expected_resp)
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
            self.logger.error(f"Exception: {repr(e)}")
            raise
        
        #except AssertionError as err:
        #    self.logger.error(f"Assertion Error: {repr(err)}")
        #    self.logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
        #    raise err 

    def test_broken_item(self):
        """Get 'corrupt' item

        The items added before Country/Institution were required will have 
        nulls for these values. This used to cause the REST API to crash and 
        return an HTML page with a 500 error. This has been fixed. This test
        will check that the fix is still working.
        """        
        #print("\n=== Testing to get 'corrupt' item ===")
        #print("GET /api/v1/components/{part_id}")
        #print("Retrieving 'corrupt' item with part_id: Z00100200017-00001")

        self.test_info["endpoint"] = f"GET : /components/Z00100200017-00001"
        self.test_info["description"] = "Get an item info"
        self.test_info["check"] = "if status=OK and see \"country_code\" and \"institution\" are null"

        try:
            resp = get_hwitem("Z00100200017-00001")
            self.assertEqual(resp['status'], "OK")
            self.assertIsNone(resp['data']['country_code'])
            self.assertIsNone(resp['data']['institution'])
        
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
            self.logger.error(f"Exception: {repr(e)}")
            raise
            #self.logger.error(f"Assertion Error: {repr(err)}")
            #self.logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            #raise err 

    def test_invalid_item(self):
        """Attempt to get an invalid item"""   
        #print("\n=== Testing to get an invalid item ===")
        #print("GET /api/v1/components/{part_id}")     
        #print("Attempting to retrieve invalid item with part_id: Z99999999999-99999")

        self.test_info["endpoint"] = f"GET : /components/Z99999999999-99999"
        self.test_info["description"] = "Get an item info"
        self.test_info["check"] = "if it fails to GET a non-existing item"

        try:
            with self.assertRaises(ra.exceptions.DatabaseError):
                resp = get_hwitem("Z99999999999-99999")
        
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
            self.logger.error(f"Exception: {repr(e)}")
            raise
    
if __name__ == "__main__":
    from Sisyphus.Configuration import config

