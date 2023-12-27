#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test/RestApiV1/Test__post_component_types.py
Copyright (c) 2022 Regents of the University of Minnesota
Author: Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger()

import os
import json
import unittest
import random

from Sisyphus.RestApiV1 import post_component, post_hwitem, patch_enable_item, patch_hwitem_subcomp

class Test__post_subcomponent(unittest.TestCase):
    
    #post an item under the part type id will be the subcomponent, 
    # retrieve part id and enable it. post containter item with subcomponent, 
    # check status. Patch the container item to remove subcomponent, check status.
    def test_post_subcomponent(self):
        testname = "post_subcomponent"
        logger.info(f"[TEST {testname}]")

        try:

            #posting new item under Test Type 002
            part_type_id = "Z00100300002"
            serial_number = "S99999"

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
                "subcomponents": {}
            }

            resp = post_hwitem(part_type_id, data)
            logger.info(f"Response from post: {resp}") 
            self.assertEqual(resp["status"], "OK")

            part_id_subcomp = resp["part_id"]

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

            resp = patch_enable_item(part_id_subcomp, data)
            logger.info(f"Response from patch: {resp}")
            self.assertEqual(resp["status"], "OK")

            #posting hwitem with subcomponent
            part_type_id = "Z00100300001"
            serial_number = f"SN{random.randint(0x00000000, 0xFFFFFFFF):08X}"
            data = {
                "comments": "unit testing",
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
                    "Comment": "Unit Test: post component with subcomponent"
                },
                "subcomponents": {"Subcomp 1" : part_id_subcomp}
            }
            resp = post_component(part_type_id, data)
            logger.info(f"response was {resp}")
            self.assertEqual(resp["status"], "OK")

            part_id_container = resp["part_id"]

             #removing subcomponent from container
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
        
        except AssertionError as err:
            logger.error(f"[FAIL {testname}]")
            logger.info(err)
            raise err

        logger.info(f"[PASS {testname}]")
    ##############################################################################

if __name__ == "__main__":
    unittest.main()

