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

import pandas as pd
import uuid
from datetime import datetime
import json
import random

pp = lambda s: print(json.dumps(s, indent=4))

def generate_excel(save_file):

    # Generate an Excel workbook for "biff" and "bongo" component types
    # A biff contains two bongos, so let's create 2 biffs and 4 bongos.
    manu_id = 7
    inst_id = 186

    biff_part_type_name, biff_part_type_id = ut.lookup_part_type_id_by_fullname("z.sandbox.hwdbunittest.biff")
    bongo_part_type_name, bongo_part_type_id = ut.lookup_part_type_id_by_fullname("z.sandbox.hwdbunittest.bongo")

    kwargs = {
        "comments": f"bulk added {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "institution_id": inst_id,
        "manufacturer_id": manu_id,
    }
    bongo_bulk = ut.bulk_add_hwitems(bongo_part_type_id, 4, **kwargs)
    biff_bulk = ut.bulk_add_hwitems(biff_part_type_id, 2, **kwargs)

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

    bongo_items = \
    [
        {
            "External ID": part_id,
            "Serial Number": str(uuid.uuid4()).upper(),
            "Institution ID": 186,
            "Manufacturer ID": 7,
            "Comments": f"generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "Color": random.choice(colors),
            "Flavor": random.choice(flavors),
        } for part_id in bongo_bulk
    ]

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

    with pd.ExcelWriter(save_file) as writer:
        df_bongo_items.to_excel(writer, sheet_name='Bongo-Items', index=False)
        df_bongo_item_images.to_excel(writer, sheet_name='Bongo-Item-Images', index=False)
        df_bongo_tests.to_excel(writer, sheet_name='Bongo-Tests', index=False)
        df_bongo_test_images.to_excel(writer, sheet_name='Bongo-Test-Images', index=False)
        df_biff_items.to_excel(writer, sheet_name='Biff-Items', index=False)
        df_biff_tests.to_excel(writer, sheet_name='Biff-Tests', index=False)


 
if __name__ == "__main__":
    generate_excel("Upload_PID.xlsx")
