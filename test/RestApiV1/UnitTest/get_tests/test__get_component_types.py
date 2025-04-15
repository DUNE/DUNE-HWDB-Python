#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Authors: 
    Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy

Test RestApiV1 functions related to Component Types
"""

from Sisyphus.Utils import UnitTest as unittest

import os
import json
import time
from datetime import datetime

from Sisyphus.RestApiV1 import get_component_type
from Sisyphus.RestApiV1 import get_hwitems
from Sisyphus.RestApiV1 import get_component_type_connectors
from Sisyphus.RestApiV1 import get_component_type_specifications
from Sisyphus.RestApiV1 import get_component_types


class Test__get_component_type(unittest.TestCase):
    
    def setUp(self):
        self.start_time = time.time()
        print(f"\nTest #{getattr(self, 'test_number', 'N/A')}: {self.__class__.__name__}.{self._testMethodName}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def tearDown(self):
        end_time = time.time()
        duration = end_time - self.start_time
        print(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test duration: {duration:.2f} seconds")


    def test_get_component_type(self):
        """Get component type"""
        print("\n=== Testing to get a component type ===")
        print("GET /api/v1/component-types/{part_type_id}")
        
        part_type_id = 'Z00100300001'
        print(f"Retrieving component type for part_type_id: {part_type_id}")
        
        resp = get_component_type(part_type_id)
        self.logger.info(f"server response:\n{json.dumps(resp, indent=4)}")

        self.assertEqual(resp['status'], "OK")
        self.assertEqual(resp['data']['connectors']['Subcomp 1'], 'Z00100300002')
 
    #-----------------------------------------------------------------------------    

    def test_get_hwitems(self):
        """Get a list of items"""
        print("\n=== Testing to get a list of items ===")
        print("GET /api/v1/component-types/{part_type_id}/components")

        part_type_id = 'Z00100110001'
        page, size = 1, 20
        print(f"Retrieving items for part_type_id: {part_type_id}, page: {page}, size: {size}")

        resp = get_hwitems(part_type_id, page=page, size=size)            
        self.logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
        
        self.assertEqual(resp['status'], "OK")
        self.assertIsInstance(resp['data'][0]['component_id'], int)
        self.assertIsInstance(resp['data'][0]['creator']['id'], int)

    #-----------------------------------------------------------------------------    
    
    def test_component_type_connectors(self):
        """Get subcomponents for component type"""
        print("\n=== Testing to get subcomponents for component type ===")
        print("GET /api/v1/component-types/{part_type_id}/connectors")

        part_type_id = 'Z00100300001' 
        print(f"Retrieving connectors for part_type_id: {part_type_id}")
        
        resp = get_component_type_connectors(part_type_id)
        self.logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
        
        self.assertEqual(resp['status'], "OK")
        self.assertEqual(resp['data']['Subcomp 1'], 'Z00100300002')

    #-----------------------------------------------------------------------------    
    
    def test_component_type_specifications(self):
        """Get specification definition for component type"""
        print("\n=== Testing to get specification definition for component type ===")
        print("GET /api/v1/component-types/{part_type_id}/specifications")
    
        part_type_id = 'Z00100300001'
        print(f"Retrieving specifications for part_type_id: {part_type_id}")
        
        resp = get_component_type_specifications(part_type_id)
        self.logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
        
        self.assertEqual(resp['status'], "OK")
        self.assertEqual(resp['data'][0]['creator'], "Alex Wagner")
        self.assertEqual(resp['data'][0]['datasheet']['Widget ID'], None)

    #-----------------------------------------------------------------------------    
    
    def test_component_types_by_proj_sys(self):
        """Get a list of component types by project and system"""  
        print("\n=== Testing to get a list of component types by project and system ===")  
        print("GET /api/v1/component-types/{project_id}/{system_id}")
    
        proj_id = 'Z'
        sys_id = 1
        page, size = 1, 100
        print(f"Retrieving component types for project: {proj_id}, system: {sys_id}, page: {page}, size: {size}")

        resp = get_component_types(proj_id, sys_id, page=page, size=size)
        self.logger.info(f"server response:\n{json.dumps(resp, indent=4)}")

        self.assertEqual(resp['status'], "OK")
        self.assertIsInstance(resp['data'][0]['category'], str)
        self.assertIsInstance(resp['data'][0]['creator']['id'], int)

    #-----------------------------------------------------------------------------    
    
    def test_component_types_by_proj_sys_subsys(self):
        """Get a list of component types by project, system, and subsystem"""
        print("\n=== Testing to get a list of component types by project, system, and subsystem ===")
        print("GET /api/v1/component-types/{project_id}/{system_id}/{subsystem_id}")
            
        proj_id = 'Z'
        sys_id = 1
        subsys_id = 1
        page, size = 1, 100
        print(f"Retrieving component types for project: {proj_id}, system: {sys_id}, subsystem: {subsys_id}, page: {page}, size: {size}")

        resp = get_component_types(proj_id, sys_id, subsys_id, page=page, size=size)
        self.logger.info(f"server response:\n{json.dumps(resp, indent=4)}")

        self.assertEqual(resp['status'], "OK")
        self.assertIsInstance(resp['data'][0]['category'], str)
        self.assertIsInstance(resp['data'][0]['creator']['id'], int)

#=================================================================================

if __name__ == "__main__":
    unittest.main(argv=config.remaining_args)
