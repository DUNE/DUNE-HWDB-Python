#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/Utils/UnitTest.py
Copyright (c) 2024 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
#logger = config.getLogger(__name__)

# Import everything from unittest so that one could import our
# module in its place and still have access to the base functionality
from unittest import *

# Import the module in its own namespace to avoid confusion between
# when we are referring to something in the original module and something
# in this module that may have overridden some functionality
import unittest

import io, traceback


class TestCase(unittest.TestCase):
    """Extends unittest.TestCase to automatically log test cases"""
    logger = config.getLogger(__name__)

    def setUp(self):
        """Logs entry into each test case"""

        self.maxDiff = 0x10000
        self.logger.info(f"[TEST {self._testMethodName}]")
        if self._testMethodDoc is not None:
            doc_first_line = self._testMethodDoc.split('\n', 1)[0]
            self.logger.info(f"description: '{doc_first_line}'")

    def tearDown(self):
        """Logs exit from each test case, and any errors found"""

        # The last thing on self._outcome.errors tells what test
        # was just run, and the reason for the failure if it failed.
        # If it didn't fail, the second part is just None.
        _, error = self._outcome.errors[-1]

        if error is None:
            self.logger.info(f"[PASS {self._testMethodName}]")
            return

        exc_type, exc, tb = error

        # Get a string for the traceback.
        # I really wanted to get the same subsegment of the traceback that
        # the unittest module displays in the terminal, where it only shows
        # the frames that are in the user code (compare what what you see
        # on the screen to what we're writing here in the log to see what I
        # mean), but I can't figure out how it does it. The code that
        # apparently cleans up the traceback really shouldn't work, because
        # **every frame** in the traceback thinks it's coming from unittest
        # even if it isn't. Maybe I'll fix it some day. TODO
        with io.StringIO() as fp:
            traceback.print_exception(None, exc, tb, limit=-10, file=fp)
            tb_str = fp.getvalue()

        self.logger.error(f"The test raised an error. Details follow.\n{tb_str}")

        self.logger.error(f"[FAIL {self._testMethodName}]")

    def assertRaises(self, *args, **kwargs):
        """Context manager that expects an exception and fails if it does not occur

        This function logs a warning message that an exception is
        (probably) about to occur, and that this is intentional.
        The purpose of this is to keep the tester who is examining
        the logs from being concerned that something needs to be 
        fixed.

        After logging the warning, this function returns the 
        context manager of the parent class. See the documentation
        for unittest.TestCase.assertRaises for more information.
        """

        self.logger.warning("The next assertion should raise "
                "an exception. This is normal.")
        
        return super().assertRaises(*args, **kwargs)

class TestProgram(unittest.TestProgram):
    """Extends unittest.TestProgram to cooperate with Configuration module

    For most executables in the DUNE HWDB Python Utility, the
    Configuration module can consume some command line arguments
    to alter the executable's behavior for the duration of the 
    call. For example, the user can add --dev or --prod to 
    switch servers. However, unittest will not recognize these
    options and will exit with an error if it sees them, so 
    we will allow Configuration to consume these, and we will
    explicitly pass what is left over, rather than let unittest
    default to using the entire sys.argv argument list.

    See the documentation for unittest.TestProgram for more
    information on the parent class.
    """

    logger = config.getLogger(__name__)
    
    def __init__(self, *args, **kwargs):
        self.logger.info("Entering TestProgram framework")

        kwargs["argv"] = config.remaining_args
        super().__init__(*args, **kwargs)    

main = TestProgram


if __name__ == "__main__":
    main(module=None)

