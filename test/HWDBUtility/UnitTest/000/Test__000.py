#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: 
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger()

from Sisyphus.HWDBUtility import Docket
import unittest

import json
pp = lambda s: print(json.dumps(s, indent=4))

class Test__000(unittest.TestCase):

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
            with open("docket.py", "r") as f:
                docket = Docket(eval(f.read()))

            pp(docket.values)
            pp(docket.sources)


        except AssertionError as err:
            logger.error(f"AssertionError: {err}")
            raise err

 
if __name__ == "__main__":
    unittest.main()
