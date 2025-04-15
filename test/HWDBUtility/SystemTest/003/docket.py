#!/usr/bin/env python
# -*- coding: utf-8 -*-

source_1 = \
{
    "Source Name": "Biff",
    "Files": ["Biff-SN-errors.xlsx"],
    "Sheets":
    [
        "Biff-Items", "Biff-Tests", #"Biff-Item_Images", "Biff-Test_Images"
    ],
    "Values":
    {
        "from source": 200,
    }
}

source_2 = \
{
    "Source Name": "Biff",
    "Files": ["Biff_2.xlsx"],
    "Sheets":
    [
        "Biff-Items"
    ],
    "Values":
    {
        "from source": 200,
    }
}

source_3 = \
{
    "Source Name": "Biff",
    "Files": ["Biff_3.xlsx"],
    "Sheets":
    [
        "Biff-Items"
    ],
    "Values":
    {
        "from source": 200,
    }
}



source_4 = \
{
    "Source Name": "Dingbat",
    "Files": ["Dingbat.xlsx", "Dingbat2.xlsx"],
}

contents = \
{
    "Docket Name": "Dingbat",
    "Sources":
    [
        source_1,
        #source_2,
        #source_3,
    ],
    "Encoders":
    [
        {
            "Encoder Name": "blank",
            "Record Type": "Item",
            "Part Type ID": "Zxxxyyyzzzz",
            "Schema": {}
        }
    ],
    "Values":
    {
        "from docket": 100,
    },
    "Includes":
    [
    ]
}
