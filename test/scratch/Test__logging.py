#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Testing some features of logging
"""
from Sisyphus.Configuration import config
logger = config.getLogger()

import unittest

class Test__logging(unittest.TestCase):
    def setUp(self):
        pass

    def test_logging(self):
        teststr = "[TEST] xx [PASS] xx [FAIL] xx [TEST xx] xx [PASS xx] xx [FAIL xx] xx"
        logger.debug(f"debug message {teststr}")
        logger.info(f"info message {teststr}")
        logger.warning(f"warning message {teststr}")
        logger.error(f"error message {teststr}")
        logger.critical(f"critical message {teststr}")

if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Testing some features of logging
"""
from Sisyphus.Configuration import config
logger = config.getLogger()

import unittest

class Test__logging(unittest.TestCase):
    def setUp(self):
        pass

    def test_logging(self):
        teststr = "[TEST] xx [PASS] xx [FAIL] xx [TEST xx] xx [PASS xx] xx [FAIL xx] xx"
        logger.debug(f"debug message")
        logger.info(f"info message")
        logger.warning(f"warning message")
        logger.error(f"error message")
        logger.critical(f"critical message")
        logger.debug(f"debug message {teststr}")
        logger.info(f"info message {teststr}")
        logger.warning(f"warning message {teststr}")
        logger.error(f"error message {teststr}")
        logger.critical(f"critical message {teststr}")

if __name__ == "__main__":
    unittest.main()

