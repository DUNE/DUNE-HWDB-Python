#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/DataModel/_HWTest.py
Copyright (c) 2024 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

import Sisyphus
from Sisyphus.Configuration import config
logger = config.getLogger(__name__)
from Sisyphus.Utils.utils import preserve_order, restore_order, serialize_for_display
import Sisyphus.RestApiV1 as ra
import Sisyphus.RestApiV1.Utilities as ut
from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus.Utils.Terminal.BoxDraw import Table
from Sisyphus.Utils.Terminal import BoxDraw
from Sisyphus.Utils import utils
import io
import json
import sys
import os
from copy import deepcopy
import re
import time
import random

class HWTest:
    #{{{
    #{{{
    _column_to_property = \
    {
        "Part Type ID": "part_type_id",
        "Part Type Name": "part_type_name",
        "Test Name": "test_name",
        "Serial Number": "serial_number",
        "External ID": "part_id",
        "Comments": "comments",
        "Test Results": "test_data",
    }
    _property_to_column = {v: k for k, v in _column_to_property.items()}
    #}}}    

    #--------------------------------------------------------------------------

    def __init__(self, *, part_type_id=None, part_type_name=None, test_name=None, AreYouSure=False):
        #{{{
        if not AreYouSure:
            raise ValueError("Don't create new HWTests this way "
                            "unless you know what you're doing!")

        self._part_type = ut.fetch_component_type(part_type_id, part_type_name)
        
        self.test_name = test_name
        if not (test_def := self._part_type["TestTypeDefs"].get(test_name, None)):
            raise ValueError(f"No test type found named '{test_name}'")
        self._test_def = test_def
        self._test_def_id = test_def["data"]["id"]
        self._test_def_datasheet = test_def["data"]["properties"]["specifications"][-1]["datasheet"]

        self._last_commit = {k: None for k in self._property_to_column.keys()}
        self._current = deepcopy(self._last_commit)
        self._is_new = False

        #Style.error.print(json.dumps(self._part_type, indent=4))
        #}}}

    #--------------------------------------------------------------------------

    def toUserData(self):
        user_record = {col_name: self._current[prop_name]
                for col_name, prop_name in self._column_to_property.items()}
        return user_record

    @classmethod
    def fromUserData(cls, user_record, encoder=None):
        #{{{
        #print(user_record.get("Part Type ID", None))
        #print(user_record.get("Part Type Name", None))
        #print(user_record.get("Test Name", None))

        #if user_record.get("Serial Number") == "3H0154":
        #    raise RuntimeError("testing error handling")


        new_hwtest = HWTest(
                part_type_id=user_record.get("Part Type ID", None),
                part_type_name=user_record.get("Part Type Name", None),
                test_name=user_record.get("Test Name", None),
                AreYouSure=True)
        new_hwtest._encoder = encoder

        user_record = deepcopy(user_record)

        if isinstance(spec := user_record.get("Test Results", None), list):
            user_record["Test Results"] = spec[0]
        
        try:
            hwdb_record = cls._get_from_hwdb(
                    part_type_id=user_record.get("Part Type ID", None),
                    part_type_name=user_record.get("Part Type Name", None),
                    part_id=user_record.get("External ID", None),
                    serial_number=user_record.get("Serial Number", None),
                    test_name=user_record.get("Test Name", None))
            new_hwtest._is_new = False
            new_hwtest._last_commit = hwdb_record
    
        except ra.NotFound:
            if cls._is_unassigned(user_record.get("External ID", None)):
                # This is fine. It just means that the item hasn't been added yet.
                new_hwtest._is_new = True
                new_hwtest._pending_item = True
            else:
                raise

        #Style.fg(0x00ff00).print("NEW DATA:", json.dumps(user_record['Test Results'], indent=4))
        #Style.fg(0x66ff00).print("OLD DATA:", json.dumps(new_hwtest._last_commit['test_data'], indent=4))
     
        # TODO: get these to merge 
        #merged = encoder.merge_records(
        #                [new_hwtest._last_commit['test_data']],
        #                [user_record['Test Results']],
        #                encoder.schema['members']['Test Results'])
        #Style.fg(0xff6600).print("RESULT", json.dumps(merged, indent=4))

 
        for col_name, prop_name in cls._column_to_property.items():
            if col_name not in user_record:
                logger.warning(f"{col_name} not in user_record")
            else:
                new_hwtest._current[prop_name] = user_record.pop(col_name, None)
        new_hwtest._current['part_id'] = new_hwtest._last_commit['part_id']

        if len(user_record) > 0:
            logger.warning(f"extra columns in user_record: {tuple(user_record.keys())}")

        #new_hwitem.normalize()
        #new_hwitem.validate()


        return new_hwtest
        #}}}

    @classmethod
    def _get_from_hwdb(cls, part_type_id=None, part_type_name=None, 
                    part_id=None, serial_number=None, test_name=None):
        #{{{
        # FIRST, let's make sure we have an Item to work with.
        kwargs = {
            "part_type_id": part_type_id,
            "part_type_name": part_type_name,
            "part_id": part_id,
            "serial_number": serial_number,
            "count": 2
        }

        if cls._is_unassigned(part_id):
            kwargs['part_id'] = None
        else:
            kwargs["serial_number"] = None

        hwitem_raw = ut.fetch_hwitems(**kwargs)

        # Raise an exception if no records are found, or more than one is found.
        if len(hwitem_raw) == 0:
            raise ra.NotFound("The arguments provided did not match any HWItems.")
        elif len(hwitem_raw) > 1:
            # TODO: we could still cache it for later.
            logger.warning(json.dumps(hwitem_raw, indent=4))
            raise ra.AmbiguousParameters("The arguments provided matched more than one HWItem.")

        _, item_node = hwitem_raw.popitem()
        it = item_node["Item"]
        sc = item_node["Subcomponents"]
        ct_all = ut.fetch_component_type(part_type_id=it["component_type"]["part_type_id"])
        ct = ct_all["ComponentType"]

        #if not (test_def := self._part_type["TestTypeDefs"].get(test_name, None)):
        #    raise ValueError(f"No test type found named '{test_name}'")
        #self._test_def = test_def
        #self._test_def_id = test_def["data"]["id"]
        #self._test_def_datasheet = test_def["data"]["properties"]["specifications"][-1]["datasheet"]

        ttd = ct_all["TestTypeDefs"][test_name]["data"]

        committed_tests = ra.get_hwitem_test(it["part_id"], ttd["id"])["data"]

        if len(committed_tests) > 0:
            existing_test_data = utils.restore_order(committed_tests[0]["test_data"])
            existing_comments = committed_tests[0]["comments"]
        else:
            existing_test_data = ttd["properties"]["specifications"][-1]["datasheet"]
            existing_comments = None

        _ = existing_test_data.pop("_meta", None)

        #print(ct["part_type_id"], it["part_id"], ttd["id"])

        #print(json.dumps(ct, indent=2))

        hwdb_record = (
        {
            "part_type_id": ct["part_type_id"],
            "part_type_name": ct["full_name"],
            "part_id": it["part_id"],
            "serial_number": it["serial_number"],
            "test_name": test_name,
            "comments": existing_comments,
            "test_data": existing_test_data,
        })


        return hwdb_record
        #}}}

    def update(self):
        #{{{
        current = self._current        
        last_commit = self._last_commit

        if self._is_unassigned(current['part_id']):
            print(current['part_id'])
            print(last_commit['part_id'])
            raise ValueError("test's part id is still unassigned")

        test_data = utils.preserve_order(current['test_data'])

        if "_meta" not in test_data:
            test_data["_meta"] = {}
        test_data["_meta"]["HWDB Utility Version"] = Sisyphus.version

        #print(json.dumps(test_data, indent=4))

        post_data = {
            "test_type": current['test_name'],
            "comments": current['comments'],
            "test_data": utils.preserve_order(current['test_data'])
        }

        #resp = ra.post_test(current['part_id'], post_data)
        resp = ra.post_test(current['part_id'], post_data)
        #print(json.dumps(resp, indent=4))
        #}}}

    def __str__(self):
        #{{{
        style_bold = Style.bold()
        style_green = Style.fg(0x33ff33).bold()
        style_yellow = Style.fg(0xdddd22).bold()

        fp = io.StringIO()

        #fp.write(json.dumps(self._current, indent=4))

        current = self._current
        last_commit = self._last_commit

        header_data = [
            ["Operation", style_green("MERGING TESTS")],
            ["Part Type ID", current['part_type_id']],
            ["Part Type Name", current['part_type_name']],
            ["Test Name", current['test_name']],
            ["External ID", current['part_id']],
            ["Serial Number", current['serial_number']],
        ]

        header_table = Table(header_data)
        header_table.set_column_width(0, 15)
        header_table.set_column_width(1, 61)
        fp.write(header_table.generate())
        fp.write("\n")

        table_data = [
            [ style_bold(s) for s in
            ['Property',        'Value'] ],
            ['Comments',         current['comments']],

            #['Test Results',    
            #        json.dumps(current['test_data'], indent=4)]
        ]

        def truncate_test_results(test_results):
            test_lines = test_results.split('\n')

            if len(test_lines) > 30:
                test_output = ('\n'.join(test_lines[:29]) 
                            + f"\n ...and {len(test_lines)-29} more lines...")
            else:
                test_output = test_results
            return test_output

        table_data.append(['Previous\nTest Results', 
                truncate_test_results(json.dumps(last_commit['test_data'], indent=4))])

        table_data.append(['Test Results', 
                truncate_test_results(json.dumps(current['test_data'], indent=4))])

        table = Table(table_data)
        table.set_row_border(1, BoxDraw.BORDER_STRONG)
        table.set_column_border(1, BoxDraw.BORDER_STRONG)
        table.set_column_width(0, 15)
        table.set_column_width(1, 81)
        #table.set_row_height(2, 30)
        fp.write(table.generate(trunc_char='▶', trunc_style=Style.fg(0x8888ff)))


        return fp.getvalue()
        #}}}
    
    @staticmethod
    def _is_unassigned(part_id):
        unassigned = (None, '', '<unassigned>', '<tbd>', '<null>')
        return (part_id is None) or (part_id.casefold() in unassigned)

    #}}}














