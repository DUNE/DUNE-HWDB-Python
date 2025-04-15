#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: 
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger()

from Sisyphus import RestApiV1 as ra
ra.session_kwargs["timeout"] = 10

from Sisyphus.HWDBUtility import Docket
import unittest

import json
pp = lambda s: print(json.dumps(s, indent=4))

from generate_excel_sn import generate_excel

class Test__SN(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        generate_excel("Upload_SN.xlsx")

        _locals = {}
        with open("docket_sn.py", "r") as f:
            exec(f.read(), globals(), _locals)
        cls.docket = Docket(_locals["contents"])

    def setUp(self):
        self.maxDiff = 0x10000
        logger.info(f"[TEST {self.id()}]")

    def tearDown(self):
        has_error = self._outcome.errors[-1][1] is not None

        if not has_error:
            logger.info(f"[PASS {self.id()}]")
        else:
            logger.error(f"[FAIL {self.id()}]")

    #-----------------------------------------------------------------------------

    def test_01(self):
        
        try:
            # TBD check the actual contents of "sources"
            self.assertEqual(len(self.docket.sources), 1)
            #pp(self.docket.sources)

        except AssertionError as err:
            logger.error(f"AssertionError: {err}")
            raise err

    #-----------------------------------------------------------------------------

    def test_02(self):
        
        try:
            self.docket.process_sources()

            # print("NEW HWITEMS")
            # pp(self.docket.new_hwitems)

            # print("UPDATE HWITEMS")
            # pp(self.docket.update_hwitems)

            # print("ENABLE HWITEMS")
            # pp(self.docket.enable_hwitems)

            # print("ATTACH SUBCOMPONENTS")
            # pp(self.docket.attach_subcomponents)

            # print("NEW TESTS")
            # pp(self.docket.new_tests)

            self.docket.update_hwdb()
        
        except AssertionError as err:
            logger.error(f"AssertionError: {err}")
            raise err

    #-----------------------------------------------------------------------------
 
if __name__ == "__main__":
    unittest.main()
