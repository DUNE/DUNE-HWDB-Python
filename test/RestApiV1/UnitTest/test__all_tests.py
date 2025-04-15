#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Authors: 
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
    Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy
"""

import sys
import os
from datetime import datetime
import time
import traceback
from io import StringIO




from Sisyphus.Utils import UnitTest as unittest
from Sisyphus.Configuration import config


from get_tests.test__get_hwitem import *
from get_tests.test__get_misc import *
from get_tests.test__get_component_types import *
from get_tests.test__get_tests import *
from get_tests.test__get_images import *

from post_tests.test__post_hwitems_bulk import *
from post_tests.test__post_subcomponent import *
from post_tests.test__post_hwitem import *
from post_tests.test__post_tests import *
from post_tests.test__post_images import *

from patch_tests.test__patch_hwitems_bulk import *
from patch_tests.test__patch_enables import *
from patch_tests.test__patch_hwitem import *

from spec_tests.test__specifications import *

class RealTimeTestResult(unittest.TextTestResult):

    def __init__(self, stream, descriptions, verbosity):
        super(RealTimeTestResult, self).__init__(stream, descriptions, verbosity)
        self.stream = stream
        self.showAll = verbosity > 1
        self.buffer = False
        self._stdout_buffer = StringIO()
        self._stderr_buffer = StringIO()
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self.test_number = 0
        self.test_results = []
        self.test_start_time = None
    
    def startTest(self, test):
        super(RealTimeTestResult, self).startTest(test)
        self.test_number += 1
        test.test_number = self.test_number
        #self.test_start_time = time.time()
        #self.stream.write(f"\nTest #{self.test_number}: {test.__class__.__name__}.{test._testMethodName}\n")
        #self.stream.write(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        #self.stream.flush()
        sys.stdout = self._stdout_buffer
        sys.stderr = self._stderr_buffer

    def stopTest(self, test):
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        test_output = self._stdout_buffer.getvalue()
        if test_output.strip():  # Only print if there's actual output
            self.stream.write(test_output)
        self.stream.write(self._stderr_buffer.getvalue())
        #end_time = time.time()
        #duration = end_time - self.test_start_time
        #self.stream.write(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        #self.stream.write(f"Test duration: {duration:.2f} seconds\n")
        self._stdout_buffer.seek(0)
        self._stdout_buffer.truncate()
        self._stderr_buffer.seek(0)
        self._stderr_buffer.truncate()
        self.stream.flush()
        super(RealTimeTestResult, self).stopTest(test)
    
    def addSuccess(self, test):
        super(RealTimeTestResult, self).addSuccess(test)
        self.test_results.append((self.test_number, "Passed", test.__class__.__name__, test._testMethodName))
        if self.showAll:
            self.stream.write("OK\n")
        else:
            self.stream.write('.')
        self.stream.flush()

    def addError(self, test, err):
        super(RealTimeTestResult, self).addError(test, err)
        self.test_results.append((self.test_number, "Failed", test.__class__.__name__, test._testMethodName))
        if self.showAll:
            self.stream.write("ERROR\n")
            self._print_error_details(test, err)
        else:
            self.stream.write('E')
        self.stream.flush()

    def addFailure(self, test, err):
        super(RealTimeTestResult, self).addFailure(test, err)
        self.test_results.append((self.test_number, "Failed", test.__class__.__name__, test._testMethodName))
        if self.showAll:
            self.stream.write("FAIL\n")
            self._print_error_details(test, err)
        else:
            self.stream.write('F')
        self.stream.flush()

    def _print_error_details(self, test, err):
        self.stream.write(self.separator1 + '\n')
        self.stream.write(f"{test.__class__.__name__}.{test._testMethodName}\n")
        self.stream.write(self.separator2 + '\n')
        self.stream.write(''.join(traceback.format_exception(*err)) + '\n')
        self.stream.flush()

    def print_summary(self):
        total_tests = len(self.test_results)
        failed_tests = sum(1 for result in self.test_results if result[1] == "Failed")
        
        self.stream.write(f"\n{failed_tests} Failed out of {total_tests} Tests:\n")
        for test_num, status, class_name, method_name in self.test_results:
            self.stream.write(f"Test #{test_num}: {status} : {class_name}.{method_name}\n")
        self.stream.flush()

class RealTimeTestRunner(unittest.TextTestRunner):
    resultclass = RealTimeTestResult

    def __init__(self, stream=sys.stderr, descriptions=True, verbosity=1,
                 failfast=False, buffer=False, resultclass=None, warnings=None,
                 *, tb_locals=False):
        super(RealTimeTestRunner, self).__init__(
            stream, descriptions, verbosity, failfast, buffer,
            resultclass, warnings, tb_locals=tb_locals)

    def _makeResult(self):
        return self.resultclass(self.stream, self.descriptions, self.verbosity)

    def run(self, test):
        result = super(RealTimeTestRunner, self).run(test)
        result.print_summary()
        return result

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])

    total_tests = suite.countTestCases()
    
    runner = RealTimeTestRunner(verbosity=2, stream=sys.stdout)
    print(f"Running {total_tests} tests:\n")
    result = runner.run(suite)

    sys.exit(not result.wasSuccessful())