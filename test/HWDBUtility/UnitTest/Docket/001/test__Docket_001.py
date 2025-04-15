#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: 
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Utils import UnitTest as unittest
from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus.HWDBUtility.Docket import Docket

import random
import json
from copy import deepcopy

class Test__Docket_001(unittest.TestCase):

    def test__open_py(self):
        filename = "docket.py"
        docket = Docket(filename=filename)
        self.assertEqual(str(docket), output1.replace("${FILENAME}", filename))

    def test__open_json(self):
        filename = "docket.json"
        docket = Docket(filename=filename)
        self.assertEqual(str(docket), output1.replace("${FILENAME}", filename))
    
    def test__open_json5(self):
        filename = "docket.json5"
        docket = Docket(filename=filename)
        self.assertEqual(str(docket), output1.replace("${FILENAME}", filename))
    
    def test__open_py_error(self):
        with self.assertRaises(ValueError):
            docket = Docket(filename="docket-error.py")


output1 = \
"""{
    "Docket Name": "${FILENAME}",
    "Values": {},
    "Sources": [
        {
            "_docket_name": "${FILENAME}",
            "Source Name": null,
            "Files": [
                "workbook1.xlsx"
            ],
            "Values": {},
            "Encoder": "_AUTO_",
            "Sheet Name": "Biff Items"
        }
    ],
    "Encoders": {}
}"""

#=================================================================================

if __name__ == "__main__":
    unittest.main()   

