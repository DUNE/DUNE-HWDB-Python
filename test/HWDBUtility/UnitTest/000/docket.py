#!/usr/bin/env python
# -*- coding: utf-8 -*-
# """
# Copyright (c) 2024 Regents of the University of Minnesota
# Author: 
#     Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
# """

{
    "Docket Name": "Docket 000",

    "Values":
    {
        "Test Value": "Docket for Test 000",
    },

    "Sources":
    [
        {
            "Source Name": "Biff",
            "Files": "Biff.xlsx",
            "Sheets": "Biff-Items",
            "Values":
            {
                "Type ID":  "Z00100300023",
            }
        },
        {
            "Files": "Bongo.xlsx",
            "Values":
            {
                "Type ID":  "Z00100300023",
            },
            "Sheets":
            [
                {
                    "Sheet Name": "Bongo-Items",
                },
                {
                    "Sheet Name": "Bongo-Test-Bounce",
                    "Values":
                    {
                        "Test Name": "Bounce",
                    },
                }
            ]
        },
        {
            "Files": "INVALID.xlsx",
            "Sheets": "INVALID-Items",
            "Values":
            {
                "Type ID":  "Z00100300023",
            }
        },
        {
            "Files": "~/Projects/DUNE-HWDB-Python/test/HWDBEncoder/000/B*.xlsx",
        },
        {
            "Files": ["Biff.xlsx", "Bongo.xlsx"],
        },
        {
            "Files": "Doohickey.csv",
        }
    ]
}
