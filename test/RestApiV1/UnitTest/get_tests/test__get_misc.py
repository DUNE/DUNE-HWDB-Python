#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Authors: 
    Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy

Test 'miscellaneous' RestApiV1 functions
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)
from Sisyphus.Utils import UnitTest as unittest

import os
import json
import sys
import time
from datetime import datetime

from Sisyphus.RestApiV1 import get_countries
from Sisyphus.RestApiV1 import whoami
from Sisyphus.RestApiV1 import get_institutions
from Sisyphus.RestApiV1 import get_manufacturers
from Sisyphus.RestApiV1 import get_projects
from Sisyphus.RestApiV1 import get_role
from Sisyphus.RestApiV1 import get_roles
from Sisyphus.RestApiV1 import get_user
from Sisyphus.RestApiV1 import get_users
from Sisyphus.RestApiV1 import get_system
from Sisyphus.RestApiV1 import get_systems
from Sisyphus.RestApiV1 import get_subsystem
from Sisyphus.RestApiV1 import get_subsystems
import Sisyphus.RestApiV1 as ra

class Test__get_misc(unittest.TestCase):
    """Test 'miscellaneous' RestApiV1 functions"""
    
    def setUp(self):
        self.start_time = time.time()
        print(f"\nTest #{getattr(self, 'test_number', 'N/A')}: {self.__class__.__name__}.{self._testMethodName}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def tearDown(self):
        end_time = time.time()
        duration = end_time - self.start_time
        print(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test duration: {duration:.2f} seconds")
    
    def test_get_countries(self):
        print("\n=== Testing to get a list of countries ===")
        print("GET /api/v1/countries")
        print("Retrieving list of countries")

        file_path = os.path.join(os.path.dirname(__file__),
                '..','ExpectedResponses', 'misc', 'countries.json')
        with open(file_path, 'r') as file:
            expected_resp = json.load(file)
        
        try:
            resp = get_countries()
             
            self.assertEqual(resp["status"], "OK")
            self.assertDictEqual(resp, expected_resp)
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err

    def test_whoami(self):
        print("\n=== Testing 'whoami' ===")
        print("GET /api/v1/users/whoami")
        print("Retrieving current user information")

        try:
            resp = whoami() 

            self.assertEqual(resp["status"], "OK")
            self.assertIsInstance(resp["data"]["full_name"], str)
            self.assertIsInstance(resp["data"]["user_id"], int)
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err

    def test_get_institutions(self):
        print("\n=== Testing to get a list of institutions ===")
        print("GET /api/v1/institutions")
        print("Retrieving list of institutions")

        try:
            resp = get_institutions()
            
            self.assertEqual(resp["status"], "OK")
            self.assertEqual(resp['data'][0]['country']['code'], "US")
            self.assertEqual(resp['data'][0]['country']['name'], "United States")
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err

    def test_get_manufacturers(self):
        print("\n=== Testing to get a list of manufacturers ===")
        print("GET /api/v1/manufacturers")
        print("Retrieving list of manufacturers")

        try:
            resp = get_manufacturers()
            
            self.assertEqual(resp["status"], "OK")
            self.assertEqual(resp['data'][0]['id'], 1)
            self.assertEqual(resp['data'][0]['name'], "Homenick Ltd")

            self.assertIsInstance(resp['data'][-1]['id'], int)
            self.assertIsInstance(resp['data'][-1]['name'], str)
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err

    def test_get_projects(self):
        print("\n=== Testing to get a list of projects ===")
        print("GET /api/v1/projects")
        print("Retrieving list of projects")

        try:
            resp = get_projects()
            
            self.assertEqual(resp["status"], "OK")
            self.assertEqual(resp['data'][1]['id'], "D")
            self.assertEqual(resp['data'][1]['name'], "DUNE")
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err

    def test_get_roles(self):
        print("\n=== Testing to get a list of roles ===")
        print("GET /api/v1/roles")
        print("Retrieving list of roles")

        try:
            resp = get_roles()            

            self.assertEqual(resp["status"], "OK")
            self.assertIsInstance(resp["data"][-1]["id"], int)
            self.assertIsInstance(resp["data"][0]["component_types"][0]["name"], str)
            self.assertIsInstance(resp["data"][0]["users"][0]["user_id"], int)
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err

    def test_get_users(self):
        print("\n=== Testing to get a list of users ===")
        print("GET /api/v1/users")
        print("Retrieving list of users")

        try:
            resp = get_users()
              
            self.assertEqual(resp["status"], "OK")
            self.assertIsInstance(resp["data"][0]["user_id"], int)
            self.assertIsInstance(resp["data"][0]["username"], str)
            self.assertIsInstance(resp["data"][-1]["user_id"], int)
            self.assertIsInstance(resp["data"][-1]["username"], str)
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err

    def test_get_user(self):
        print("\n=== Testing to get a specific user ===")
        print("GET /api/v1/users/{user_id}")
        print("Retrieving user with ID: 13615")

        userid = 13615 #alex
        file_path = os.path.join(os.path.dirname(__file__),
                '..','ExpectedResponses', 'misc', 'alex_whoami.json')
        with open(file_path, 'r') as file:
            expected_resp = json.load(file)
        
        try:
            resp = get_user(userid)

            self.assertEqual(resp["status"], "OK")
            self.assertDictEqual(resp, expected_resp)
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err

    def test_get_role(self):
        print("\n=== Testing to get a specific role ===")
        print("GET /api/v1/roles/{role_id}")
        print("Retrieving role with ID: 4")

        role_id = 4
        try:
            resp = get_role(role_id)

            self.assertEqual(resp["status"], "OK")
            self.assertEqual(resp["data"]["id"], role_id)
            self.assertEqual(resp["data"]["name"], "tester")
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err

    def test_get_subsystems(self):
        print("\n=== Testing to get a list of subsystems from a project and system ===")
        print("GET /api/v1/subsystems/{project_id}/{system_id}")
        print("Retrieving subsystems for project 'Z', system 1")

        proj_id = 'Z'
        sys_id = 1
        
        try:
            resp = get_subsystems(proj_id, sys_id)

            self.assertEqual(resp["status"], "OK")
            self.assertIsInstance(resp["data"][0]["creator"]["id"], int)
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err

    def test_get_subsystems_empty(self):
        """Get a list of subsystems from a project and system"""

        print("\n=== Testing to get a list of subsystems from a non-existent project (should return empty list) ===")
        print("GET /api/v1/subsystems/{project_id}/{system_id}")
        print("Attempting to retrieve subsystems for non-existent project 's', system 1")

        file_path2 = os.path.join(os.path.dirname(__file__), 
                '..','ExpectedResponses', 'misc', 'empty_list.json')
        with open(file_path2 , 'r') as file:
            err_expected_resp = json.load(file)
        
        proj_id = 's'
        sys_id = 1            

        try:
            resp = get_subsystems(proj_id, sys_id)          
            logger.debug(f"server response:\n{json.dumps(resp, indent=4)}")
            
            self.assertEqual(resp["status"], "OK")
            self.assertListEqual(resp["data"], [])
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err

    def test_get_subsystem(self): 
        """Get a specific subsystem""" 
        print("\n=== Testing to get a specific subsystem ===")
        print("GET /api/v1/component-types/{project_id}/{system_id}/{subsystem_id}")
        print("Retrieving subsystem for project 'Z', system 1, subsystem 1")
            
        proj_id = 'Z'
        sys_id = 1
        subsys_id = 1
        
        file_path = os.path.join(os.path.dirname(__file__),
                '..','ExpectedResponses', 'misc', 'projZsys1subsys1.json')
        with open(file_path, 'r') as file:
            expected_resp = json.load(file)

        try:
            resp = get_subsystem(proj_id, sys_id, subsys_id)

            self.assertEqual(resp["status"], "OK")
            self.assertDictEqual(expected_resp, resp)
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err
    
    def test_get_subsystem__bad(self):
        print("\n=== Testing to get a nonexistent subsystem (should raise error) ===")
        print("GET /api/v1/component-types/{project_id}/{system_id}/{subsystem_id}")
        print("Attempting to retrieve nonexistent subsystem for project 'Z', system 1, subsystem 9")

        proj_id = 'Z'
        sys_id = 1
        subsys_id = 9

        with self.assertRaises(ra.exceptions.DatabaseError):
            logger.warning("NOTE: The following subtest raises an exception. This is normal.")
            resp = get_subsystem(proj_id, sys_id, subsys_id)

    def test_get_systems(self):
        print("\n=== Testing to get a list of systems from a project ===")
        print("GET /api/v1/systems/{project_id}")
        print("Retrieving systems for project 'Z'")

        proj_id = 'Z'
        
        try:
            resp = get_systems(proj_id)
            
            self.assertEqual(resp["status"], "OK")
            self.assertIsInstance(resp["data"][0]["comments"], str)
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err
        
    def test_get_systems__nonexistent(self):
        print("\n=== Testing to get a list of systems from a non-existent project (should return empty list) ===")
        print("GET /api/v1/systems/{project_id}")
        print("Attempting to retrieve systems for non-existent project 's'")
           
        proj_id = 's'

        try:
            resp = get_systems(proj_id)

            self.assertEqual(resp["status"], "OK")
            self.assertEqual(resp["pagination"]["total"], 0)
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err

    def test_get_system(self):
        print("\n=== Testing to get a system ===")
        print("GET /api/v1/component-types/{project_id}/{system_id}")
        print("Retrieving system for project 'Z', system 1")

        file_path = os.path.join(os.path.dirname(__file__), 
                '..','ExpectedResponses', 'misc', 'projZsy.json')
        with open(file_path , 'r') as file:
            expected_resp = json.load(file)
        proj_id = 'Z'
        sys_id = 1

        try:
            resp = get_system(proj_id, sys_id)
            
            self.assertEqual(resp["status"], "OK")
            self.assertDictEqual(resp, expected_resp)
        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err
    
    def test_get_system__bad(self):
        """Attempt to get a non-existent system

        This should raise a DatabaseError.
        """

        print("\n=== Testing to get a non-existent system (should raise error) ===")
        print("GET /api/v1/component-types/{project_id}/{system_id}")
        print("Attempting to retrieve non-existent system for project 'X', system 80")

        proj_id = 'X'
        sys_id = 80

        with self.assertRaises(ra.exceptions.DatabaseError):
            logger.warning("NOTE: The following subtest raises an exception. This is normal.")
            resp = get_system(proj_id, sys_id)

if __name__ == "__main__":
    unittest.main(argv=config.remaining_args)