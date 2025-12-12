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
        #super(RealTimeTestResult, self).startTest(test)
        super().startTest(test)

        self.test_number += 1
        test.test_number = self.test_number

        # Initialize storage for this test
        test.test_info = {
            "error": "",
            "description": "",
            "check": "",
            "ended": "",
            "duration": "",
            "endpoint": "",
        }

        sys.stdout = self._stdout_buffer
        sys.stderr = self._stderr_buffer

    def stopTest(self, test):
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

        captured_out = self._stdout_buffer.getvalue()
        captured_err = self._stderr_buffer.getvalue()

        #test_output = self._stdout_buffer.getvalue()
        test.test_info["output"] = captured_out

        #if test_output.strip():  # Only print if there's actual output
        #    self.stream.write(test_output)
        if captured_err:
            test.test_info["error"] = captured_err

        end_time = time.time()
        duration = end_time - test.start_time
        test.test_info["ended"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        test.test_info["duration"] = duration

        #self.stream.write(self._stderr_buffer.getvalue())
        # Print during run
        if captured_out.strip():
            self.stream.write(captured_out)
        if captured_err:
            self.stream.write(captured_err)

        self._stdout_buffer.seek(0)
        self._stdout_buffer.truncate()
        self._stderr_buffer.seek(0)
        self._stderr_buffer.truncate()

        self.stream.flush()
        #super(RealTimeTestResult, self).stopTest(test)
        super().stopTest(test)
    
    def addSuccess(self, test):
        #super(RealTimeTestResult, self).addSuccess(test)
        super().addSuccess(test)

        #self.test_results.append((self.test_number, "Passed", test.__class__.__name__, test._testMethodName))
        self.test_results.append({
            "num": self.test_number,
            "status": "✅ Passed",
            "class": test.__class__.__name__,
            "method": test._testMethodName,
            "info": test.test_info,
        })


        if self.showAll:
            self.stream.write("OK\n")
        else:
            self.stream.write('.')
        self.stream.flush()

    def addError(self, test, err):
        #super(RealTimeTestResult, self).addError(test, err)
        super().addError(test, err)

        #self.test_results.append((self.test_number, "Failed", test.__class__.__name__, test._testMethodName))
        self.test_results.append({
            "num": self.test_number,
            "status": "⚠️ Failed",
            "class": test.__class__.__name__,
            "method": test._testMethodName,
            "info": test.test_info,   # includes output, error, description, custom
            "traceback": ''.join(traceback.format_exception(*err)),
        })

        if self.showAll:
            self.stream.write("ERROR\n")
            self._print_error_details(test, err)
        else:
            self.stream.write('E')
        self.stream.flush()

    def addFailure(self, test, err):
        #super(RealTimeTestResult, self).addFailure(test, err)
        super().addFailure(test, err)
        #self.test_results.append((self.test_number, "Failed", test.__class__.__name__, test._testMethodName))

        self.test_results.append({
            "num": self.test_number,
            "status": "⚠️ Failed",
            "class": test.__class__.__name__,
            "method": test._testMethodName,
            "info": test.test_info,
            "traceback": ''.join(traceback.format_exception(*err)),
        })

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
        self.stream.write("\n===== FINAL TEST SUMMARY =====\n")
        #total_tests = len(self.test_results)
        #failed_tests = sum(1 for result in self.test_results if result[1] == "Failed")
        total = len(self.test_results)
        #failures = sum(1 for t in self.test_results if t["status"] == "Failed")
        failures = sum(1 for t in self.test_results if "Failed" in t["status"])
        self.stream.write(f"{failures} failed out of {total} tests.\n\n")
        
        #self.stream.write(f"\n{failed_tests} Failed out of {total_tests} Tests:\n")

        #for test_num, status, class_name, method_name in self.test_results:
        #    self.stream.write(f"Test #{test_num}: {status} : {class_name}.{method_name}\n")
        #self.stream.flush()

        last_class = None
        for t in self.test_results:
            class_name = t["class"]

            # If class changed since last test, print separator
            if class_name != last_class:
                header_map = {
                    "Test__get_misc": "GET misc: /countries/, /institutions/, /manufacturers/, /projects/... etc",
                    "Test__get_component_type": "GET /component-types/",
                    "Test__get_tests": "GET /component-types/<type id>/test-types/, /component-test-types/, and /components/<pid>/tests/<test type name>",
                    "Test__get_hwitems": "GET /components/",
                    "Test__get_images": "GET /component-types/<type id>/images and /components/<pid>/images",
                    "Test__post_hwitem": "POST /component-types/<pid>/components",
                    "Test__post_hwitems_bulk": "POST /component-types/<pid>/bulk-add",
                    "Test__post_tests": "POST /components/<pid>/tests",
                    "Test__post_subcomponent": "POST /component-types/<pid>/components",
                    "Test__post_images": "POST /components/<pid>/images",
                    "Test__specifications": "PATCH /component-types/<type id>",
                    "Test__patch_hwitem": "PATCH /components/<pid> and PATCH /components/<pid>/status",
                    "Test__patch_hwitems_bulk": "PATCH /component-types/Z00100300001/bulk-update",
                }
                header = header_map.get(class_name, class_name)
                self.stream.write(f"\n==== {header} ====\n")
                last_class = class_name

            self.stream.write(f"Test #{t['num']}: {t['status']} : {t['info']['ended']} (Duration: {t['info']['duration']:.2f} seconds) : {t['info']['endpoint']}\n")
            self.stream.write(f"    Description : {t['info']['description']}\n")
            if t["info"]["check"]:
                self.stream.write(f"    How to check: {t['info']['check']}\n")
            self.stream.write(f"    Class.Method: {t['class']}.{t['method']}\n")

            #if "ended" in t["info"]:
            #    self.stream.write(f"    Ended       : {t['info']['ended']} (Duration: {t['info']['duration']:.2f} seconds)\n")

            #if "duration" in t["info"]:
            #    self.stream.write(f"  Duration: {t['info']['duration']:.2f} seconds\n")

            if t["info"]["error"].strip():
                self.stream.write(f"    Error Output:\n{t['info']['error']}\n")

            if "traceback" in t:
                self.stream.write(f"    Traceback   :\n{t['traceback']}\n")

            self.stream.write("\n")

    def printErrors(self):
        # Suppress the default error/failure dump
        # to avoid the duplications of error messages in the log
        pass

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

# =====================================================================
# CUSTOM ORDERING OF TESTS
# =====================================================================

# Example — fully specify the exact order you want
TEST_ORDER = [
    "Test__get_misc.test_get_countries",                                #  1 GET /countries
    "Test__get_misc.test_get_institutions",                             #  2 GET /institutions
    "Test__get_misc.test_get_manufacturers",                            #  3 GET /manufacturers
    "Test__get_misc.test_get_roles",                                    #  4 GET /roles
    "Test__get_misc.test_get_role",                                     #  5 GET /roles/4
    "Test__get_misc.test_get_users",                                    #  6 GET /users
    "Test__get_misc.test_get_user",                                     #  7 GET /users/13615
    "Test__get_misc.test_whoami",                                       #  8 GET /users/whoami
    "Test__get_misc.test_get_projects",                                 #  9 GET /projects
    "Test__get_misc.test_get_systems",                                  # 10 GET /systems/Z
    "Test__get_misc.test_get_systems__nonexistent",                     # 11 GET /systems/s
    "Test__get_misc.test_get_subsystems",                               # 12 GET /subsystems/Z/1
    "Test__get_misc.test_get_subsystems_empty",                         # 13 GET /subsystems/s/1
    "Test__get_component_type.test_get_component_type",                 # 14 GET /component-types/Z00100300001
    "Test__get_component_type.test_component_type_connectors",          # 15 GET /component-types/Z00100300001/connectors
    "Test__get_component_type.test_component_type_specifications",      # 16 GET /component-types/Z00100300001/specifications
    "Test__get_component_type.test_get_hwitems",                        # 17 GET /component-types/Z00100300001/components
    "Test__get_component_type.test_component_types_by_proj_sys",        # 18 GET /component-types/Z/1
    "Test__get_component_type.test_component_types_by_proj_sys_subsys", # 19 GET /component-types/Z/1/1
    "Test__get_tests.test_test_types",                                  # 20 GET /component-types/Z00100300001/test-types
    "Test__get_tests.test_test_type",                                   # 21 GET /component-types/Z00100300001/test-types/492
    "Test__get_tests.test_test_type_by_oid",                            # 22 GET /component-test-types/1
    "Test__get_tests.test_test_hwitem",                                 # 23 GET /components/Z00100300001-00021/tests/unittest1
    "Test__get_hwitems.test_normal_item",                               # 24 GET /components/Z00100300001-00021
    "Test__get_hwitems.test_broken_item",                               # 25 GET /components/Z00100200017-00001
    "Test__get_hwitems.test_invalid_item",                              # 26 GET /components/Z99999999999-99999
    "Test__get_images.test__get_component_type_image_list",             # 27 GET /component-types/Z00100300006/images and /img/image_id
    "Test__get_images.test__get_hwitem_image_list",                     # 28 GET /components/Z00100300006-00001/images and /img/image_id
    "Test__post_hwitem.test__post_hwitem",                              # 29 POST /component-types/Z00100300001/components
    "Test__post_hwitem.test__post_hwitem__bad_spec",                    # 30 POST /component-types/Z00100300001/components
    "Test__post_hwitem.test__post_hwitem__extra_spec",                  # 31 POST /component-types/Z00100300001/components
    "Test__post_hwitem.test__post_hwitem__bad_fields",                  # 32 POST /component-types/Z00100300001/components
    "Test__post_hwitems_bulk.test_post_hwitems_bulk",                   # 33 POST /component-types/Z00100300001/bulk-add
    "Test__post_tests.test_post_test_good",                             # 34 POST /components/Z00100300001-00360/tests
    "Test__post_tests.test_post_test_missing",                          # 35 POST /components/Z00100300001-00360/tests
    "Test__post_subcomponent.test_post_subcomponent",                   # 36 POST /component-types/<type id>/components and PATCH /components/<pid>/subcomponents
    "Test__post_images.test__post_hwitem_image",                        # 37 POST /components/<pid>/images
    "Test__specifications.test__specifications",                        # 38 PATCH /component-types/Z00100300030
    "Test__patch_hwitem.test_patch_hwitem",                             # 39 PATCH /components/<pid>
    "Test__patch_hwitem.test_patch_hwitem_subcomp",                     # 40 PATCH /components/<pid>/subcomponents
    "Test__patch_hwitems_bulk.test_patch_hwitems_bulk",                 # 41 PATCH /component-types/Z00100300001/bulk-update
]

def build_ordered_suite():
    suite = unittest.TestSuite()
    global_namespace = globals()

    for test_path in TEST_ORDER:
        class_name, method_name = test_path.split(".")
        cls = global_namespace[class_name]
        suite.addTest(cls(method_name))

    return suite

if __name__ == "__main__":

    # Run in my order, instead of just alphabetically
    #suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    suite = build_ordered_suite()

    total_tests = suite.countTestCases()
    
    #runner = RealTimeTestRunner(verbosity=2, stream=sys.stdout)
    runner = RealTimeTestRunner(verbosity=1, stream=sys.stdout)
    print(f"Running {total_tests} tests:\n")
    result = runner.run(suite)

    sys.exit(not result.wasSuccessful())
