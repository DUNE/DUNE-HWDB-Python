#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test/RestApiV1/Test__get_component_types.py
Copyright (c) 2023 Regents of the University of Minnesota
Authors: 
    Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger()

import unittest
import os
import json

import warnings
import urllib3
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

#from Sisyphus.RestApiV1._RestApiV1 import _get
from Sisyphus.RestApiV1 import get_component_type
from Sisyphus.RestApiV1 import get_hwitems
from Sisyphus.RestApiV1 import get_component_type_connectors
from Sisyphus.RestApiV1 import get_component_type_specifications
from Sisyphus.RestApiV1 import get_component_types

class Test__get_component_type(unittest.TestCase):
    def setUp(self):
        self.maxDiff = 0x10000
    
    #-----------------------------------------------------------------------------    

    def test_get_component_type(self):
        testname = "get_component_type"
        logger.info(f"[TEST {testname}]")

        try:
            part_type_id = 'D00501341001'
            file_path = os.path.join(
                    os.path.dirname(__file__),
                    'ExpectedResponses', 'componentTypes', 
                    'part-type-id-D00501341001.json')
            with open(file_path, 'r') as file:
                expected_resp = json.load(file)
            resp = get_component_type(part_type_id)
            self.assertEqual(resp['status'], "OK")
            self.assertDictEqual(resp, expected_resp)
 
        except AssertionError as err:
            logger.error(f"[FAIL {testname}]")
            logger.info(err)
            logger.debug(f"({testname}) response:\n{json.dumps(resp, indent=4)}")
            raise err
        logger.info(f"[PASS {testname}]")
    
    #-----------------------------------------------------------------------------    

    def test_get_hwitems(self):
        testname = "get_hwitems"
        logger.info(f"[TEST {testname}]")

        try:
            part_type_id = 'D00501341001'
            #part_type_id = 'Z00100110001'
            file_path = os.path.join(
                    os.path.dirname(__file__),
                    'ExpectedResponses', 'componentTypes', 
                    'components_page1.json')
            with open(file_path, 'r') as file:
                expected_resp = json.load(file)

            page, size = 1, 100
 
            resp = get_hwitems(part_type_id, page=page, size=size)            
            
            self.assertEqual(resp['status'], "OK")
            #self.assertDictEqual(resp, expected_resp)

        except AssertionError as err:
            logger.error(f"[FAIL {testname}]")
            logger.info(err)
            logger.debug(f"({testname}) response:\n{json.dumps(resp, indent=4)}")
            raise err
        logger.info(f"[PASS {testname}]")

    #-----------------------------------------------------------------------------    
    
    def test_component_type_connectors(self):
        testname = "get_component_type_connectors"
        logger.info(f"[TEST {testname}]")
        
        try:
            part_type_id = 'D00501341001' #change to different id
            file_path = os.path.join(
                    os.path.dirname(__file__),
                    'ExpectedResponses', 'componentTypes', 
                    'connectors.json')
            with open(file_path, 'r') as file:
                expected_resp = json.load(file)
            
            resp = get_component_type_connectors(part_type_id)
            
            self.assertEqual(resp['status'], "OK")
            self.assertDictEqual(resp, expected_resp)
        
        except AssertionError as err:
            logger.error(f"[FAIL {testname}]")
            logger.info(err)
            logger.debug(f"({testname}) response:\n{json.dumps(resp, indent=4)}")
            raise err
        logger.info(f"[PASS {testname}]")
    
    #-----------------------------------------------------------------------------    
    
    def test_component_type_specifications(self):
        testname = "get_component_type_specifications"
        logger.info(f"[TEST {testname}]")
        
        try:
            part_type_id = 'D00501341001'
            file_path = os.path.join(
                    os.path.dirname(__file__),
                    'ExpectedResponses', 'componentTypes', 
                    'specifications.json')
            with open(file_path, 'r') as file:
                expected_resp = json.load(file)
            
            resp = get_component_type_specifications(part_type_id)
            self.assertEqual(resp['status'], "OK")
            self.assertDictEqual(resp, expected_resp)
            
        except AssertionError as err:
            logger.error(f"[FAIL {testname}]")
            logger.info(err)
            logger.debug(f"({testname}) response:\n{json.dumps(resp, indent=4)}")
            raise err
        logger.info(f"[PASS {testname}]")


    #-----------------------------------------------------------------------------    
    
    def test_component_types_by_proj_sys(self):
        testname = "get_component_types_by_proj_sys"
        logger.info(f"[TEST {testname}]")
        
        try:
            file_path = os.path.join(
                    os.path.dirname(__file__), 
                    'ExpectedResponses', 'componentTypes', 
                    'list-components-by-sys.json')
            with open(file_path , 'r') as file:
                expected_resp = json.load(file)
            proj_id = 'D'
            sys_id = 1

            page, size = 1, 100
            fields = [] 
 
            resp = get_component_types(proj_id, sys_id, page=page, size=size)

            self.assertEqual(resp['status'], "OK")
            self.assertDictEqual(resp,expected_resp)

        except AssertionError as err:
            logger.error(f"[FAIL {testname}]")
            logger.info(err)
            logger.debug(f"({testname}) response:\n{json.dumps(resp, indent=4)}")
            raise err
        logger.info(f"[PASS {testname}]")

    #-----------------------------------------------------------------------------    
    
    def test_component_types_by_proj_sys_subsys(self):
        testname = "get_component_types_by_proj_sys_subsys"
        logger.info(f"[TEST {testname}]")

        try:
            file_path = os.path.join(
                    os.path.dirname(__file__), 
                    'ExpectedResponses', 'componentTypes', 
                    'comp-types-D-1-1.json')
            with open(file_path , 'r') as file:
                expected_resp = json.load(file)
            
            proj_id = 'D'
            sys_id = 1
            subsys_id = 1
            page, size = 1, 100
            fields = []
 
            resp = get_component_types(proj_id, sys_id, subsys_id, page=page, size=size)

            self.assertEqual(resp['status'], "OK")
            self.assertDictEqual(resp,expected_resp)

        except AssertionError as err:
            logger.error(f"[FAIL {testname}]")
            logger.info(err)
            logger.debug(f"({testname}) response:\n{json.dumps(resp, indent=4)}")
            raise err
        logger.info(f"[PASS {testname}]")

##############################################################################

if __name__ == "__main__":
    unittest.main()
