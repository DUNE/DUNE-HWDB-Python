#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: 
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Utils import UnitTest as unittest

from Sisyphus.HWDBUtility.HWItem import HWItem

import random
import json
from copy import deepcopy

from Sisyphus.Utils.Terminal.Style import Style

class Test__Encoder(unittest.TestCase):

    def test__create_from_ItemRecord(self):
        ...

    def test__get_from_HWDB(self):
        # TODO: add tests with different subsets of these parameters
        # TODO: add tests where part type name and id are in conflict
        # TODO: add tests that return 0 or 2+ results
        part_type_id = "Z00100300022"
        part_type_name = "Z.Sandbox.HWDBUnitTest.biff"
        part_id = "Z00100300022-00057"
        serial_number = "059313D3-B728-4C3D-857C-1AB9DAC93232"

        hwitem = HWItem.fromHWDB(
                    part_type_id=part_type_id, 
                    part_type_name=part_type_name,
                    part_id=part_id,
                    serial_number=serial_number,
                )

        print(json.dumps(hwitem.toUserData(), indent=4))

        #print(HWItem.user_role_check(part_type_name=part_type_name))

    @unittest.skip("not now")
    def test__user_role_check(self):
        #{{{
        """Tests check for whether user has role for a part type"""
        part_type_name = "Z.Sandbox.HWDBUnitTest.biff"
        self.assertTrue(HWItem.user_role_check(part_type_name=part_type_name),
                    "user was expected to have a role for this component type")

        part_type_name = "Z.Sandbox.HWDBUnitTest.wibble"
        self.assertFalse(HWItem.user_role_check(part_type_name=part_type_name),
                    "user was expected to not have a role for this component type")
        #}}}



#=================================================================================

if __name__ == "__main__":
    unittest.main()   

