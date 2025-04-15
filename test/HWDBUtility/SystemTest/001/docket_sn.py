#!/usr/bin/env python
# -*- coding: utf-8 -*-
# """
# Copyright (c) 2024 Regents of the University of Minnesota
# Author: 
#     Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
# """

contents = \
{
    "Docket Name": "Docket 001",
    "Sources":
    [
        {
            "Source Name": "Bongos and Biffs",
            "Files": "Upload_SN.xlsx",
            #"Part Type Name": "Z.Sandbox.HWDBUnitTest.snork",
            "Sheets": 
            [   
                {
                    "Sheet Name": "Bongo-Items",
                    #"Sheet Type": "Item",
                    #"Part Type ID": "Z00100300023",
                    "Values":
                    {
                        "Manufacturer ID": 7,
                    },
                    "Encoder": "@auto",
                },
                {
                    "Sheet Name": "Biff-Items",
                    "Sheet Type": "Item",
                    "Part Type Name": "Z.Sandbox.HWDBUnitTest.biff",
                    "Values":
                    {
                        "Institution ID": 186,
                    }
                }
            ]
        }
    ],
    "Encoders": []
}


