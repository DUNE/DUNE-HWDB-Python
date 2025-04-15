#!/usr/bin/env python
# -*- coding: utf-8 -*-
# """
# Copyright (c) 2024 Regents of the University of Minnesota
# Author: 
#     Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
# """

sources = []

encoders = \
[
    {
        "Encoder Name": "Item Encoder",
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
    {
        "Encoder Name": "Results IV",
        "Sheet Type": "Test",
        "Part Type Name": "Z.Sandbox.HWDBUnitTest.snork",
        "Test Name": "IV SiPM Characterization",
    },
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
    {
        "Encoder Name": "IV SiPM Noise Test",
        "Sheet Type": "Test",
        "Part Type Name": "Z.Sandbox.HWDBUnitTest.snork",
        "Test Name": "IV SiPM Noise Test",
    },
    {
        "Encoder Name": "SiPM Mass Test Results",
        "Sheet Type": "Test",
        "Part Type Name": "Z.Sandbox.HWDBUnitTest.snork",
        "Test Name": "SiPM Mass Test Results",
    },
]




contents = \
{
    "Docket Name": "My Docket",
    "Sources": sources,
    "Encoders": encoders,
}
