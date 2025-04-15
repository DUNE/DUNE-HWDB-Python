#!/usr/bin/env python

result = \
{
    "SiPM_Strip_ID": "171",
    "Content Manager": "HWDB Python Utility",
    "Contents":
    [
        {
            "Date": "31-05-2023-16:45 UTC",
            "Location": "Ferrara",  
            "Opertor": "Tommaso Giammaria",
            "Thermal Cycle": 3,
            "Polarization": "Rev",
            "Temperature": "LN2",
            "Acquisition_Time": 120,
            "Weighted_Threshold_Charge": 870,
            "(SiPM_Location)":
            [
                {
                    "SiPM Location": 0,
                    "OV": 4,
                    "Counts": 671,
                    "Status": "Success",
                    "Comment": "",
                },
            ]   
        },
    ],
    "_encoder":
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
}


