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

from Sisyphus import RestApiV1 as ra


class Test__specifications(unittest.TestCase):
    """Tests handling of Specifications and Test Results

    Specifications is the free-form database field for Items, and 
    Test Results is the equivalent free-form field for Tests.
    """
    
    #-------------------------------------------------------------------------

        

    def test__specifications(self):
        #{{{
        """Tests ability to change item specifications"""

        part_type_id = "Z00100300030"
       

        # Set Specifications
        # 
        self.logger.info(f"Setting specifications for {part_type_id}")
        component_def = \
        {
            "comments": "updating via REST API",
            "connectors": {},
            "manufacturers": [7, 50],
            "name": "jabberwock",
            "part_type_id": part_type_id,
            "properties":
            {
                "specifications":
                {
                    "datasheet":
                    {
                        "Flavor": None,
                        "Color": None,
                    },
                }
            },
            "roles": [4]
        }

        resp = ra.patch_component_type(part_type_id, component_def)
        self.assertEqual(resp['status'], 'OK')

        # Add Item
        #
        self.logger.info(f"attempting to add new item")
        serial_number = f"SN{random.randint(0x00000000, 0xFFFFFFFF):08X}"
        item_data = {
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
                "Color": "Red",
                "Flavor": "Strawberry",
            },
            "subcomponents": {}
        }

        resp = ra.post_hwitem(part_type_id, item_data)
        self.assertEqual(resp['status'], 'OK')
        first_item_part_id = resp['part_id']
        self.logger.info(f"added item: {resp['part_id']}")


        # Change Spec
        #
        self.logger.info("Changing the specifications")
        component_def['properties']['specifications']['datasheet'] = \
        {
            "Flavour": None,
            "Colour": None,
        }
        resp = ra.patch_component_type(part_type_id, component_def)
        self.assertEqual(resp['status'], 'OK')


        # Add "bad" item
        #
        self.logger.info("attempting to add an item with old specs (should fail)")
        serial_number = f"SN{random.randint(0x00000000, 0xFFFFFFFF):08X}"
        item_data['serial_number'] = serial_number

        with self.assertRaises(ra.BadSpecificationFormat):
            resp = ra.post_hwitem(part_type_id, item_data)

        # Add "good" item
        self.logger.info("attempting to add an item with new specs (should succeed)")
        item_data['specifications'] = \
        {
            "Colour": "Blue",
            "Flavour": "Raspberry"
        }
        resp = ra.post_hwitem(part_type_id, item_data)
        self.assertEqual(resp['status'], 'OK')
        self.logger.info(f"added item: {resp['part_id']}")

        ### DISABLE this part of the test for now.
        '''
        # Try to patch the first item by leaving the old spec fields and adding
        # new ones to it
        resp = ra.get_hwitem(first_item_part_id)
        old_item_data = resp['data']
        self.assertEqual(resp['status'], 'OK')
                
        edited_item_data = \
        {
            "comments": old_item_data['comments'],
            "manufacturer": {"id": old_item_data['manufacturer']['id']},
            "part_id": old_item_data['part_id'],
            'serial_number': old_item_data['serial_number'],
            'specifications': 
            {
                **old_item_data['specifications'][0],
                "Colour": None,
                "Flavour": None,
            }
        }
        print(json.dumps(edited_item_data, indent=4))
        resp = ra.patch_hwitem(first_item_part_id, edited_item_data)
        print(resp)
        self.assertEqual(resp['status'], 'OK')
        '''

        #}}}
    #-------------------------------------------------------------------------
    ##############################################################################

if __name__ == "__main__":
    unittest.main()

