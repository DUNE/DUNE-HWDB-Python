#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Authors:
    Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy

Tests bulk adding items
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

from Sisyphus.RestApiV1 import post_hwitems_bulk

class Test__post_hwitems_bulk(unittest.TestCase):
    """Tests bulk adding items"""
    
    def setUp(self):
        self.start_time = time.time()
        print(f"\nTest #{getattr(self, 'test_number', 'N/A')}: {self.__class__.__name__}.{self._testMethodName}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def tearDown(self):
        end_time = time.time()
        duration = end_time - self.start_time
        print(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test duration: {duration:.2f} seconds")
    
    def test_post_hwitems_bulk(self):
        print("\n=== Testing to post multiple Items in bulk ===")
        print("POST /api/v1/component-types/{part_type_id}/bulk-add")


        part_type_id = "Z00100300001"
        data = {
            "comments": "Here are some comments",
            "component_type": {
                "part_type_id": part_type_id
            },
            "count": 2,
            "country_code": "US",
            "institution": {
            "id": 186
            },
            "manufacturer": {
                "id": 7
            },
            #"status": {"id": 3} # bulk doesn't allow this yet.
        }

        logger.info(f"Posting bulk components: part_type_id={part_type_id}")
        resp = post_hwitems_bulk(part_type_id, data)
        logger.info(f"Response from post: {resp}")

        self.assertEqual(resp["status"], "OK")

        part_id1 = resp["data"][0]["part_id"]
        part_id2 = resp["data"][1]["part_id"]

        logger.info(f"New parts result: part_id1={part_id1}, part_id2={part_id2}")
        print(f"Two new Items have been created with part_ids: {part_id1} and {part_id2}")

#=================================================================================

if __name__ == "__main__":
    unittest.main(argv=config.remaining_args)