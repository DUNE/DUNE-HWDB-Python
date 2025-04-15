#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.Utils.utils import preserve_order, restore_order, serialize_for_display
from Sisyphus.Utils.Terminal.Style import Style
import Sisyphus.RestApiV1 as ra
import Sisyphus.RestApiV1.Utilities as ut
from Sisyphus.DataModel import HWItem
from Sisyphus.DataModel import HWTest
#from Sisyphus.HWDBUtility.PDFLabels import PDFLabels

import multiprocessing.dummy as mp # multiprocessing interface, but uses threads instead
import json
from uuid import uuid4 as uuid
import time
from datetime import datetime


green = Style.fg(0x00ff00)
jdump = lambda s: green.print(json.dumps(serialize_for_display(s), indent=4))


_lock = mp.threading.Lock()

_debug_no_async = False
_num_threads = 25

class JobManager:

    def __init__(self, parent, job_requests, num_threads=_num_threads):
        #{{{
        self.parent = parent
        logger.debug(f"initializing JobManager with num_threads={num_threads}")
        self.thread_pool = mp.Pool(processes=num_threads)

        if _debug_no_async:
            self._apply = self.thread_pool.apply
        else:
            self._apply = self.thread_pool.apply_async

        self.item_job_total = 0
        self.test_job_total = 0
        self.item_image_job_total = 0
        self.test_image_job_total = 0

        self.item_job_count = 0
        self.test_job_count = 0
        self.item_image_job_count = 0
        self.test_image_job_count = 0
        
        self.item_jobs = {}
        self.test_jobs = {}
        self.item_image_jobs = {}
        self.test_image_jobs = {}

        self.add_jobs(job_requests)
        #}}}

    def add_jobs(self, job_requests):
        #{{{
        # Let's count up each type of job first
        for job_request in job_requests:
            record_type = job_request["Record Type"]
            if record_type == "Item":
                self.item_job_total += 1
            if record_type == "Test":
                self.test_job_total += 1
            if record_type == "Item Image":
                self.item_image_job_total += 1
            if record_type == "Test Image":
                self.test_image_job_total += 1

        while job_requests and not hasattr(self, "_exception"):
            job_request = job_requests.pop(0)
            record_type = job_request["Record Type"]
            
            if record_type == "Item":
                self.add_item(job_request)
            if record_type == "Test":
                self.add_test(job_request)
            if record_type == "Item Image":
                self.add_item_image(job_request)
            if record_type == "Test Image":
                self.add_test_image(job_request)

        self.thread_pool.close()
        self.thread_pool.join()

        if hasattr(self, "_exception"):
            raise(self._exception)
        #}}}


    def execute(self, submit=False):

        #sn_index = {}
        #
        #for job_num in sorted(self.item_jobs.keys()):
        #    job = self.item_jobs[job_num]
        #    pt_index = sn_index.setdefault(job.part_type_id, {})
        #    
        #    # TODO: check for serial number conficts
        #    # print(job_num, (job.part_type_id, job.part_id, job.serial_number, job._sn_conflicts))

        def update_part_id(part_type_id, part_id, serial_number):
            # find any tests with the same part_type and serial_number
            # but don't have the part_id updated yet and update them.
            for merge_test in self.test_jobs.values():
                if HWTest._is_unassigned(merge_test._current['part_id']):
                    if (merge_test._current['part_type_id'] == part_type_id
                            and merge_test._current['serial_number'] == serial_number):
                        merge_test._current['part_id'] = part_id
    
        # .....................................................................

        def execute_item_jobs():

            #{{{
            # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
            
            def execute_item_core():
                # Update the "core" part of the item, i.e., all but subcomponents
                
                if self.item_jobs:
                    Style.info.print(f"    \u2022 Item Jobs: 0 / {len(self.item_jobs)}\x1b[K")
                else:
                    return

                for job_index in sorted(self.item_jobs.keys()):
                    job = self.item_jobs[job_index]
                    logger.info(f"Item Job:\n{job}")
                    if submit:
                        # store this value, because it will change after updating
                        is_new = job.is_new()

                        # update the job
                        job.update_core()
                        job.update_enabled()
                        job.update_location()

                        if is_new:
                            # update the part id in tests
                            # (this is only necessary for new items, because old items
                            # will already have their part id's looked up)
                            # TODO: what if the user has changed the serial number??
                            update_part_id(job.part_type_id, job.part_id, job.serial_number)
                        #hwitems_touched.append(job.part_id)
                    else:
                        time.sleep(0.01)
                    
                    Style.info.print(f"\x1b[F    \u2022 Item Jobs: {job_index} / "
                                f"{len(self.item_jobs)}\x1b[K")
       
            # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
            
            def execute_item_clear_subcomponents():
                # Clear any subcomponents that have changed.
                # We do this instead of just attaching the new ones directly 
                # because it's possible for an item to want to attach a subcomp
                # that another item currently owns but is planning to change to
                # a different one.

                if self.item_jobs:
                    Style.info.print(f"    \u2022 Evaluating subcomponents: 0 / {len(self.item_jobs)}\x1b[K")
                else:
                    return

                for job_index in sorted(self.item_jobs.keys()):
                    job = self.item_jobs[job_index]

                    if submit:
                        job.release_subcomponents()

                    else:
                        time.sleep(0.01)
                    
                    Style.info.print(f"\x1b[F    \u2022 Evaluating subcomponents: {job_index} / "
                                f"{len(self.item_jobs)}\x1b[K")


            # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
            
            def execute_item_attach_subcomponents():
                
        
                if self.item_jobs:
                    Style.info.print(f"    \u2022 Updating subcomponents: 0 / {len(self.item_jobs)}\x1b[K")
                else:
                    return

                for job_index in sorted(self.item_jobs.keys()):
                    job = self.item_jobs[job_index]

                    if submit:
                        job.update_subcomponents()

                    else:
                        time.sleep(0.01)
                    
                    Style.info.print(f"\x1b[F    \u2022 Updating subcomponents: {job_index} / "
                                f"{len(self.item_jobs)}\x1b[K")

            # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
           
            #hwitems_touched = []
 
            execute_item_core()
            execute_item_clear_subcomponents()
            execute_item_attach_subcomponents()

            #hwitems_touched.sort()
            #logger.info(f"Making labels for: {hwitems_touched}")
            # 
            #if hwitems_touched:
            #    pdflabels = PDFLabels(hwitems_touched)
            #    pdflabels.use_default_label_types()
            #    pdflabels.generate_label_sheets("ItemLabels.pdf")

            #}}}

        # .....................................................................
       
        def execute_test_jobs(): 
            if self.test_jobs:
                Style.info.print(f"    \u2022 Test Jobs: 0 / {len(self.test_jobs)}\x1b[K")
            else:
                return
            
            for job_index in sorted(self.test_jobs.keys()):
                job = self.test_jobs[job_index]

                if submit:
                    job.update()
                else:
                    time.sleep(0.01)

                Style.info.print(f"\x1b[F    \u2022 Test Jobs: {job_index} / "
                            f"{len(self.test_jobs)}\x1b[K")

        # .....................................................................
        
        def execute_item_image_jobs():
            if self.item_image_jobs:
                Style.info.print(f"    \u2022 Item Image Jobs: 0 / {len(self.item_image_jobs)}\x1b[K")
            else:
                return

            logger.info(f"{self.item_image_jobs}")

            for job_index in sorted(self.item_image_jobs.keys()):
                job = self.item_image_jobs[job_index]

                if submit:

                    if job['Data']['External ID'] is None:

                        resp = ut.fetch_hwitems(
                                        job['Part Type ID'],
                                        job['Part Type Name'], 
                                        job['Data']['External ID'],
                                        job['Data']['Serial Number'])
                        #print(json.dumps(resp, indent=4))
                        job['Data']['External ID'] = list(resp)[0]

                    #print(job['Part Type ID'], 
                    #    job['Part Type Name'], 
                    #    job['Data']['External ID'],
                    #    job['Data']['Serial Number'],
                    #    job['Data']['Comments'], 
                    #    sep='\n')

                    for image_job in job['Data']['Images']:

                        data = {"comments": image_job['Comments']}
                        resp = ra.post_hwitem_image(
                                job['Data']['External ID'], 
                                data, 
                                image_job['Image File'])

                else:
                    time.sleep(0.01)
                
                Style.info.print(f"\x1b[F    \u2022 Item Image Jobs: {job_index} / "
                            f"{len(self.item_image_jobs)}\x1b[K")

        # .....................................................................
        
        if submit:
            Style.notice.print(f"Executing Jobs")
        else:
            Style.notice.print(f"Executing Jobs (SIMULATED! Use '--submit' to commit to the HWDB)")
                
        if (not self.item_jobs and not self.test_jobs and not self.item_image_jobs
                        and not self.test_image_jobs):
            Style.error.print("    No jobs to execute")
            return

        execute_item_jobs()
        execute_test_jobs()
        execute_item_image_jobs()

    def error_callback(self, *args, **kwargs):
        #print("error callback:", args, kwargs)
        self.thread_pool.terminate()
        self._exception = args[0]

    def regular_callback(self, *args, **kwargs):
        #print("callback:", args, kwargs)
        pass

    def add_item(self, job_request):
        def async_add_item(job_request):
            with _lock:
                self.item_job_count += 1
                item_job_number = self.item_job_count
                self.display_job_queue_status()

            hwitem = HWItem.fromUserData(job_request['Data'])

            with _lock:
                self.item_jobs[item_job_number] = hwitem
                self.display_job_queue_status()

        self._apply(async_add_item, (job_request,), {}, self.regular_callback, self.error_callback)
                 
    def add_test(self, job_request):
        def async_add_test(job_request):
            with _lock:
                self.test_job_count += 1
                test_job_number = self.test_job_count
                self.display_job_queue_status()

            hwtest = HWTest.fromUserData(job_request['Data'])

            with _lock:
                self.test_jobs[test_job_number] = hwtest
                self.display_job_queue_status()
        
        self._apply(async_add_test, (job_request,), {}, self.regular_callback, self.error_callback)


    def add_item_image(self, job_request):
        #print('add item image')
        #print(job_request)   
        def async_add_item_image(job_request):
            with _lock:
                self.item_image_job_count += 1
                item_image_job_number = self.item_image_job_count
                self.display_job_queue_status()

            with _lock:
                self.item_image_jobs[item_image_job_number] = job_request
                self.display_job_queue_status()
                 
        self._apply(async_add_item_image, (job_request,), {}, self.regular_callback, self.error_callback)


    def add_test_image(self, job_request):
        print('add test image')

    def display_job_queue_status(self):
        #{{{
        if hasattr(self, "_exception"):
            #print("[display_job_queue_status: ignoring because of exceptions]")
            return

        if not hasattr(self, "_job_types_found"):
            Style.notice.print("Queueing Job Requests")
            self._job_types_found = 0

        if self._job_types_found:
            print(f"\x1b[{self._job_types_found}F", end='')

        job_types_found = 0

        if self.item_job_total:
            job_types_found += 1
            Style.info.print(f"    \u2022 Item Jobs: {len(self.item_jobs)} / "
                    f"{self.item_job_total}\x1b[K")
        
        if self.test_job_total:
            job_types_found += 1
            Style.info.print(f"    \u2022 Test Jobs: {len(self.test_jobs)} / "
                    f"{self.test_job_total}\x1b[K")
        
        if self.item_image_job_total:
            job_types_found += 1
            Style.info.print(f"    \u2022 Item Image Jobs: {len(self.item_image_jobs)} / "
                    f"{self.item_image_job_total}\x1b[K")
        
        if self.test_image_job_total:
            job_types_found += 1
            Style.info.print(f"    \u2022 Test Image Jobs: {len(self.test_image_jobs)} / "
                    f"{self.test_image_job_total}")

        self._job_types_found = job_types_found
        #}}}
























