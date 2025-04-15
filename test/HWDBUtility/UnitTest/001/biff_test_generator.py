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
from Sisyphus.RestApiV1 import Utilities as ut

import argparse
import pandas as pd
import uuid
from datetime import datetime
import json
import random
import os

pp = lambda s: print(json.dumps(s, indent=4))



class BiffTestGenerator:
    manu_id = 7
    inst_id = 186
    country_code = "CH" # for tests where we add it, intentionally use the wrong one
    biff_part_type_name, biff_part_type_id = \
                    ut.lookup_part_type_id_by_fullname("z.sandbox.hwdbunittest.biff")
    bongo_part_type_name, bongo_part_type_id = \
                    ut.lookup_part_type_id_by_fullname("z.sandbox.hwdbunittest.bongo")
    colors = [
        "Red", "Green", "Blue", "Yellow", 
        "Black", "Brown", "Orange", "Violet", 
        "Pink", "Maroon", "Gold", "White",
    ]

    flavors = [
        "Chocolate", "Vanilla", "Strawberry", "Butterscotch",
        "Almond", "Lemon", "Grape", "Raspberry",
        "Maple", "Blueberry", "Watermelon", "Coffee",
    ]

    images = [
        "../iamges/apple.jpeg",
        "../images/banana.jpeg",
        "../images/broccoli.jpeg",
        "../images/dice.jpeg",
        "../images/laughingcat.jpeg",
        "../images/lightbulb.jpeg",
        "../images/raccoon.jpeg",
        "../images/runningdog.jpeg",
    ]
    def __init__(self, **kwargs):

        self.settings = \
        {
            "test_name": "test_biff_upload",
            "num_items": 1,
            "reserve_eids": False,
            "create_subcomponents": True,
            "sheets":
            {
                "items": True,
                "tests": True,
                "item_images": True,
                "test_images": True,
            },
            "sheet_header": 
            {
                "Sheet Type": True,
                "Part Type ID": True,
                "Part Type Name": True,
                "Manufacturer ID": True,
                "Institution ID": True,
                "Country Code": True,
            },
            "item_columns":
            {
                "Serial Number": True,
                "Manufacturer ID": True,
                "Institution ID": True,
                "Country Code": True,
                "Specifications": True,
            }
        }
        
        self._reserve_items() 
        self._create_biff_items()
        self._create_bongo_items()

        pp(self.biff_items)
        pp(self.bongo_items)

        self._create_excel()


    def _reserve_items(self):
        kwargs = {
            "comments": f"bulk added {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "institution_id": self.inst_id,
            "manufacturer_id": self.manu_id,
        }

        if self.settings["reserve_eids"]:
            self.biff_items = [ {"External ID": part_id} for part_id in 
                    ut.bulk_add_hwitems(biff_part_type_id, self.settings["num_items"], **kwargs) ]
            if self.settings["create_subcomponents"]:
                self.bongo_items = [ {"External ID": part_id} for part_id in 
                    ut.bulk_add_hwitems(bongo_part_type_id, 2*self.settings["num_items"], **kwargs) ]
        else:
            self.biff_items = [ 
                    {
                        "External ID": "",
                        "Serial Number": str(uuid.uuid4()).upper(),
                    } 
                    for i in range(self.settings["num_items"]) ]
            if self.settings["create_subcomponents"]:
                self.bongo_items = [ 
                        {
                            "External ID": "",
                            "Serial Number": str(uuid.uuid4()).upper(),
                        } 
                        for i in range(2*self.settings["num_items"]) ]



    def _create_biff_items(self):
        for i, biff_item in enumerate(self.biff_items):
            if self.settings["reserve_eids"] and self.use_serial:
                biff_item["Serial Number"] = str(uuid.uuid4()).upper(),
            if not self.settings["sheet_header"]["Institution ID"]:
                biff_item["Institution ID"] = self.inst_id
            if not self.settings["sheet_header"]["Manufacturer ID"]:
                biff_item["Manufacturer ID"] = self.manu_id
            
            biff_item["Comments"] = f"generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            biff_item["Length"] = random.randint(8000, 12000) / 100
            biff_item["Width"] = random.randint(8000, 12000) / 100
            biff_item["Height"] = random.randint(8000, 12000) / 100

            if self.settings["create_subcomponents"]:
                if self.settings["reserve_eids"]:
                    biff_item["Left Bongo"] = self.bongo_items[i*2]["External ID"]
                    biff_item["Right Bongo"] = self.bongo_items[i*2+1]["External ID"]
                else:
                    biff_item["Left Bongo"] = self.bongo_items[i*2]["Serial Number"]
                    biff_item["Right Bongo"] = self.bongo_items[i*2+1]["Serial Number"]


    def _create_bongo_items(self):
        if not self.settings["create_subcomponents"]:
            return

        for bongo_item in self.bongo_items:       
            if self.settings["reserve_eids"] and self.use_serial:
                bongo_item["Serial Number"] = str(uuid.uuid4()).upper(),
            if not self.settings["sheet_header"]["Institution ID"]:
                bongo_item["Institution ID"] = self.inst_id
            if not self.settings["sheet_header"]["Manufacturer ID"]:
                bongo_item["Manufacturer ID"] = self.manu_id
            
            bongo_item["Comments"] = f"generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            bongo_item["Color"] = random.choice(self.colors)
            bongo_item["Flavor"] = random.choice(self.flavors)
 
    def _create_excel(self):

        test_name = self.settings["test_name"]
        filename = test_name + ".xlsx"
        if not os.path.exists(test_name):
            os.makedirs(test_name)
        filename = os.path.join(test_name, filename)


        writer = pd.ExcelWriter(filename)



        biff_items_header = {}
        sh = self.settings["sheet_header"]
        if sh["Sheet Type"]:
            biff_items_header["Sheet Type"] = "Item"
        if sh["Part Type ID"]:
            biff_items_header["Type ID"] = self.biff_part_type_id
        if sh["Part Type Name"]:
            biff_items_header["Type Name"] = self.biff_part_type_name
        if sh["Manufacturer ID"]:
            biff_items_header["Manufacturer ID"] = self.manu_id
        if sh["Institution ID"]:
            biff_items_header["Institution ID"] = self.inst_id
        if sh["Country Code"]:
            biff_items_header["Country Code"] = self.country_code

        if len(biff_items_header.keys()) > 0:
            df_biff_items_header = pd.DataFrame([biff_items_header]).transpose()
        df_biff_items = pd.DataFrame(self.biff_items)

        if len(biff_items_header.keys()) > 0: 
            df_biff_items_header.to_excel(writer, sheet_name='Biff-Items', index=True, header=False)
            df_biff_items.to_excel(writer, sheet_name='Biff-Items', index=False, 
                                        startrow=len(biff_items_header.keys())+1)
        else:
            df_biff_items.to_excel(writer, sheet_name='Biff-Items', index=False)


        writer.close()


def generate_excel(args):

    # Generate an Excel workbook for "biff" and "bongo" component types
    # A biff contains two bongos, so let's create 2 biffs and 4 bongos.

    bongo_tests = \
    [
        {
            "External ID": bongo["External ID"],
            "Serial Number": bongo["Serial Number"],
            "Comments": f"generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "Score": random.randint(0, 100),
            "Test Result": "NA",
        } for bongo in bongo_items
    ]
    for bongo in bongo_tests:
        bongo["Test Result"] = "Pass" if bongo["Score"] >= 80 else "Fail"

    bongo_item_images = \
    [
        {
            "External ID": bongo["External ID"],
            "Serial Number": bongo["Serial Number"],
            "Comments": f"generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "Image File": random.choice(images),
        } for bongo in bongo_items
    ]
    
    bongo_test_images = \
    [
        {
            "External ID": bongo["External ID"],
            "Serial Number": bongo["Serial Number"],
            "Comments": f"generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "Image File": random.choice(images),
        } for bongo in bongo_items
    ]


    biff_items = \
    [
        {
            "External ID": part_id,
            "Serial Number": str(uuid.uuid4()).upper(),
            "Institution ID": 186,
            "Manufacturer ID": 7,
            "Comments": f"generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "Length": random.randint(8000, 12000) / 100,
            "Width": random.randint(8000, 12000) / 100,
            "Height": random.randint(8000, 12000) / 100,
            "Left Bongo": bongo_items[i*2]["Serial Number"],
            "Right Bongo": bongo_items[i*2+1]["Serial Number"],
        } for i, part_id in enumerate(biff_bulk)
    ]

    biff_tests = \
    [
        {
            "External ID": biff["External ID"],
            "Serial Number": biff["Serial Number"],
            "Comments": f"generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "Score": random.randint(0, 100),
            "Result": "NA",
        } for biff in biff_items
    ]
    for biff in biff_tests:
        biff["Test Result"] = "Pass" if biff["Score"] >= 80 else "Fail"

    df_bongo_items = pd.DataFrame(bongo_items)
    df_bongo_item_images = pd.DataFrame(bongo_item_images)
    df_bongo_tests = pd.DataFrame(bongo_tests)
    df_bongo_test_images = pd.DataFrame(bongo_test_images)
    df_biff_items = pd.DataFrame(biff_items)
    df_biff_tests = pd.DataFrame(biff_tests)

    with pd.ExcelWriter(args.filename) as writer:
        df_bongo_items.to_excel(writer, sheet_name='Bongo-Items', index=False)
        df_bongo_item_images.to_excel(writer, sheet_name='Bongo-Item-Images', index=False)
        df_bongo_tests.to_excel(writer, sheet_name='Bongo-Tests', index=False)
        df_bongo_test_images.to_excel(writer, sheet_name='Bongo-Test-Images', index=False)
        df_biff_items.to_excel(writer, sheet_name='Biff-Items', index=False)
        df_biff_tests.to_excel(writer, sheet_name='Biff-Tests', index=False)


def parse():
    parser = argparse.ArgumentParser(
        add_help=True,
        parents=[config.arg_parser],
        description="Creates a test Excel workbook")
    util_group = parser.add_argument_group("Generate Excel Utility Options")
    util_group.add_argument("filename", metavar="<filename>")
    idtype_group = util_group.add_mutually_exclusive_group(required=True)
    idtype_group.add_argument("--serial-number", "--sn", dest="sn", action="store_true")
    idtype_group.add_argument("--external-id", "--eid", dest="eid", action="store_true")
    util_group.add_argument("--header-rows", dest="header", action="store_true")
    args, unknowns = parser.parse_known_args()

    return args
 
if __name__ == "__main__":
    #args = parse()
    #generate_excel(args)
    bg = BiffTestGenerator()


