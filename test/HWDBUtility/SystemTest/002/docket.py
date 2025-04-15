#!/usr/bin/env python
# -*- coding: utf-8 -*-
# """
# Copyright (c) 2024 Regents of the University of Minnesota
# Author: 
#     Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
# """

item_manifest_excel = \
{
    "Source Name": "SiPM Item Manifest",
    "Files": "SiPM-item-manifest.xlsx",
    #"Sheet Type": "Item",
    "Values":
    {
        "Sample Value 1": 1,
    },
    "Part Type Name": "Z.Sandbox.HWDBUnitTest.snork",
    "Encoder": "SiPM Item (from source info)",
}

item_manifest_csv = \
{
    "Source Name": "SiPM Item Manifest CSV",
    "Files": "SiPM-item-manifest.csv",
    "Sheet Type": "Item",
    "Values":
    {
        "Sample Value 1": 1,
    },
    #"Encoder": "SiPM Item",
}

item_manifest_csv_staggered = \
{
    "Source Name": "SiPM Item Manifest CSV",
    "Files": "SiPM-item-manifest_staggered.csv",
    "Sheet Type": "Item",
    "Values":
    {
        "Sample Value 1": 1,
    },
    #"Encoder": "SiPM Item",
}

item_manifest_csv_single = \
{
    "Source Name": "SiPM Item Manifest CSV",
    "Files": "SiPM-item-manifest_single.csv",
    "Sheet Type": "Item",
    "Values":
    {
        "Sample Value 1": 1,
    },
    #"Encoder": "SiPM Item",
}


item_manifest_csv_no_locals = \
{
    "Source Name": "SiPM Item Manifest CSV",
    "Files": "SiPM-item-manifest_no_locals.csv",
    "Sheet Type": "Item",
    "Values":
    {
        "Sample Value 1": 1,
    },
    #"Encoder": "SiPM Item",
}

test_DN = \
{
    "Source Name": "Dark Noise SiPM Counts",
    "Files": "Dark-noise-SiPM-counts.xlsx",
    "Sheets":
    [
        {
            "Sheet Name": "Sheet1",
            "Sheet Type": "Test",
            "Encoder": "Dark Noise SiPM Counts",
        }
    ]
}

sources = \
[
    item_manifest_excel,
    #item_manifest_csv,
    #item_manifest_csv_staggered,
    #item_manifest_csv_single,
    #item_manifest_csv_no_locals,
    #test_DN,
]

encoders = \
[
    {
        "Encoder Name": "SiPM Item",
        "Sheet Type": "Item",
        "Part Type Name": "Z.Sandbox.HWDBUnitTest.snork",
        "Specifications":
        {
            "Vendor_Delivery_ID": "string",
            "Vendor_Box_Number": "integer",
            "Tray_Number": "integer",
            "SiPM_Strip_ID": "string",
            "Test_Box_ID": "string",
            "Documentation": "string",
        },
    },
#    {
#        "Encoder Name": "Results IV",
#        "Sheet Type": "Test",
#        "Part Type Name": "Z.Sandbox.HWDBUnitTest.snork",
#        "Test Name": "IV SiPM Characterization",
#    },
    {
        "Encoder Name": "Dark Noise SiPM Counts",
        "Sheet Type": "Test",
        "Part Type Name": "Z.Sandbox.HWDBUnitTest.snork",
        "Test Name": "Dark Noise SiPM Counts",
        
        "Test Results":
        {
            "SiPM_Strip_ID": "string",
            "Content Manager":
            {
                "type": "string",
                "value": "HWDB Python Utility",
            },
            "Contents":
            {
                "type": "group",
                "key": ["Date", "Location"],
                "members":
                {
                    "SiPM_Strip_ID": "string",
                    "Date": "string",
                    "Location": "string",
                    "Operator": "string",
                    "Thermal_Cycle": "integer",
                    "Polarization": "string",
                    "Temperature": "string",
                    "Acquisition_Time": "float",
                    "Weighted_Threshold_Charge": "integer",
                    "SiPM Location":
                    {
                        "type": "group",
                        "key": ["SiPM_Location"],
                        "members":
                        {
                            "SiPM_Location": "integer",
                            "OV": "float",
                            "Counts": "integer",
                            "Status": "string",
                            "Comment": "string"
                        },
                    }
                },
            }
        }
    },
#    {
#        "Encoder Name": "IV SiPM Noise Test",
#        "Sheet Type": "Test",
#        "Part Type Name": "Z.Sandbox.HWDBUnitTest.snork",
#        "Test Name": "IV SiPM Noise Test",
#    },
#    {
#        "Encoder Name": "SiPM Mass Test Results",
#        "Sheet Type": "Test",
#        "Part Type Name": "Z.Sandbox.HWDBUnitTest.snork",
#        "Test Name": "SiPM Mass Test Results",
#    },
]

contents = \
{
    "Docket Name": "My Docket",
    "Sources": sources,
    "Encoders": encoders,
}

import json
print(json.dumps(contents, indent=4))
