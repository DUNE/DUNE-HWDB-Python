#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: 
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Utils import UnitTest as unittest
from Sisyphus.HWDBUtility import SheetWriter

import os, shutil

class Test__SheetWriter(unittest.TestCase):
    """Test writing Excel spreadsheets"""

    #{{{ setup/teardown
    @classmethod
    def setUpClass(cls):
        '''Create the 'output' directory'''

        super().setUpClass()

        cls.output_path = os.path.join(
                os.path.dirname(__file__),
                "output")
        shutil.rmtree(cls.output_path, ignore_errors=True)
        os.mkdir(cls.output_path)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
    #}}}

    #-------------------------------------------------------------------------

    def test__create_sheet(self):
        filename = os.path.join(self.output_path, "workbook1.xlsx")

        writer = SheetWriter.ExcelWriter(filename)

        header = \
        {
            "Part Type ID": "Zxxxyyyzzzzz",
            "Part Type Name": "Z.x.y.name",
            "Record Type": "Test",
            "Test Name": "Turtle Test",
        }

        table = \
        [
            {
                "External ID": None,
                "Serial Number": "00000001",
                "Comments": "I like turtles!",
                "T:DATA": "{'Likes Turtles': true}",
            },
            {
                "External ID": None,
                "Serial Number": "12345678901234567890",
                "Comments": "I don't like turtles! I really don't like them!",
                "T:DATA": "{'Likes Turtles': 'false'}",
            }
        ]
        writer.add_sheet("Turtle Test", header, table)
        writer.close()

    
#=============================================================================

if __name__ == "__main__":
    unittest.main()
