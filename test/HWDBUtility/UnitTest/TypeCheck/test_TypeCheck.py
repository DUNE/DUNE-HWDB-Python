#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: 
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.HWDBUtility.SheetReader import Cell
from Sisyphus.HWDBUtility import TypeCheck as tc
import math
import numpy as np
import unittest
import json


class TestCaseLogger(unittest.TestCase):

    def setUp(self):
        self.maxDiff = 0x10000
        logger.info(f"[TEST {self.id()}]")


    def tearDown(self):
        has_error = self._outcome.errors[-1][1] is not None

        if not has_error:
            logger.info(f"[PASS {self.id()}]")
        else:
            logger.error(f"[FAIL {self.id()}]")

class Test__TypeCheck(TestCaseLogger): #unittest.TestCase):
        
    def cast_tester(self, datatype, value, expected_result, should_warn=False):
        try:
            cell_kwargs = \
            {
                "source": "unit test",
                "location": "n/a",
                "warnings": [],
                "datatype": datatype,
                "value": value,
            }
            logger.info(f"Testing {type(value).__name__} '{value}' as '{datatype}' => "
                        f"{type(expected_result).__name__} '{expected_result}'"
                        + (" (warn)" if should_warn else ""))
            cell_in = Cell(**cell_kwargs)
            cell_out = tc.cast(cell_in)

            # I fucking hate NaN. We need to check this specifically.
            if type(expected_result) == float and math.isnan(expected_result):
                self.assertTrue(type(cell_out.value) == float and math.isnan(cell_out.value))

            else:
                # Check that not only is the value the same, but the type is as
                # well. This should catch any stupid "np.int64" types that Pandas
                # seems to like.
                self.assertEqual(cell_out.value, expected_result)
                self.assertEqual(type(cell_out.value), type(expected_result))            

            if should_warn:
                self.assertTrue(len(cell_out.warnings)>0, 
                        "The operation did not give warnings as expected.")
            else:
                self.assertTrue(len(cell_out.warnings)==0, 
                        "The operation gave unexpected warnings.")
        except AssertionError as err:
            logger.error(f"Assertion error: output was "
                        f"{type(cell_out.value).__name__} '{repr(cell_out.value)}'")
            raise
        

    #-----------------------------------------------------------------------------

    def test__any(self):
        #{{{
        # Test casting to "any"
        # This should mostly leave things alone, except for list/dict types,
        # and numpy types should go to their python equivalent 
        # (e.g., np.int64 => int) 
        try:
            self.cast_tester("any", None, None)
            self.cast_tester("any", "", "")
            self.cast_tester("any", float("nan"), float("nan"))
            self.cast_tester("any", "[]", [])
            self.cast_tester("any", [], [])
            self.cast_tester("any", "{}", {})
            self.cast_tester("any", {}, {})
            self.cast_tester("any", "abc", "abc")
            self.cast_tester("any", "123", "123")
            self.cast_tester("any", 123, 123)
            self.cast_tester("any", np.int64(123), 123)
            self.cast_tester("any", 123.0, 123.0)
            self.cast_tester("any", np.float64(123), 123.0)
            self.cast_tester("any", True, True)
            self.cast_tester("any", False, False)
            self.cast_tester("any", "True", "True")
            self.cast_tester("any", "False", "False")
            self.cast_tester("any", "Yes", "Yes")
            self.cast_tester("any", "No", "No")
            self.cast_tester("any", 1, 1)
            self.cast_tester("any", 0, 0)
        except AssertionError as err:
            logger.error(f"AssertionError: {err}")
            raise
        #}}}
    
    #-----------------------------------------------------------------------------
    
    def test__str(self):
        #{{{
        # Test casting to "str"
        try:
            self.cast_tester("str", None, "None")
            self.cast_tester("str", "", "")
            self.cast_tester("str", float("nan"), "nan")
            self.cast_tester("str", "[]", "[]")
            self.cast_tester("str", [], "[]")
            self.cast_tester("str", "{}", "{}")
            self.cast_tester("str", {}, "{}")
            self.cast_tester("str", "abc", "abc")
            self.cast_tester("str", "123", "123")
            self.cast_tester("str", 123, "123")
            self.cast_tester("str", np.int64(123), "123")
            self.cast_tester("str", 123.0, "123.0")
            self.cast_tester("str", np.float64(123), "123.0")
            self.cast_tester("str", True, "True")
            self.cast_tester("str", False, "False")
            self.cast_tester("str", "True", "True")
            self.cast_tester("str", "False", "False")
            self.cast_tester("str", "Yes", "Yes")
            self.cast_tester("str", "No", "No")
            self.cast_tester("str", 1, "1")
            self.cast_tester("str", 0, "0")
        except AssertionError as err:
            logger.error(f"AssertionError: {err}")
            raise
        #}}}
   
    #-----------------------------------------------------------------------------
    
    def test__int(self):
        #{{{
        # Test casting to "int"
        try:
            self.cast_tester("int", None, None, True)
            self.cast_tester("int", "", "", True)
            self.cast_tester("int", float("nan"), float("nan"), True)
            self.cast_tester("int", "[]", "[]", True)
            self.cast_tester("int", [], [], True)
            self.cast_tester("int", "{}", "{}", True)
            self.cast_tester("int", {}, {}, True)
            self.cast_tester("int", "abc", "abc", True)
            self.cast_tester("int", "123", 123, False)
            self.cast_tester("int", "123.4", "123.4", True)
            self.cast_tester("int", 123, 123, False)
            self.cast_tester("int", np.int64(123), 123, False)
            self.cast_tester("int", 123.0, 123, False)
            self.cast_tester("int", 123.4, 123.4, True)
            self.cast_tester("int", np.float64(123), 123, False)
            self.cast_tester("int", True, True, True)
            self.cast_tester("int", False, False, True)
            self.cast_tester("int", "True", "True", True)
            self.cast_tester("int", "False", "False", True)
            self.cast_tester("int", "Yes", "Yes", True)
            self.cast_tester("int", "No", "No", True)
            self.cast_tester("int", 1, 1, False)
            self.cast_tester("int", 0, 0, False)
        except AssertionError as err:
            logger.error(f"AssertionError: {err}")
            raise
        #}}}
   
    #-----------------------------------------------------------------------------
    #============================================================================= 

if __name__ == "__main__":
    unittest.main()
