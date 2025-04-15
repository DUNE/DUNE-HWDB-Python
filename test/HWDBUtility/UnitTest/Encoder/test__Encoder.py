#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: 
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.Utils import UnitTest as unittest

from Sisyphus.HWDBUtility import SheetReader
from Sisyphus.HWDBUtility import Encoder

#import unittest
import random
import json
from copy import deepcopy
from Sisyphus.Utils.Terminal.Style import Style
printcolor = lambda c, s: print(Style.fg(c)(s))

KW_TYPE = "type"
KW_KEY = "key"
KW_MEMBERS = "members"

#{{{
encoder_DNSC = \
{
    "Encoder Name": "Dark Noise SiPM Counts",
    "Record Type": "Test",
    "Part Type Name": "Z.Sandbox.HWDBUnitTest.snork",
    #"Part Type ID": "Z00100300022",
    "Test Name": "Dark Noise SiPM Counts",

    "Options":
    {
        "Create Missing Item": False,
        "Case Lenience": False,
        "Space Lenience": False,
        "Item Key Duplication": "warning", # "overwrite", "disallow"
        "Test Key Duplication": "warning", # "overwrite", "disallow"
        "Sparse Sheet": False,
    },
    
    "Schema": # Indicates where to find the values to populate the record
    {
        # "Implied" fields don't need to be stated unless they're being
        # pulled from another column.
        "Serial Number":
        {
            KW_TYPE: "string,null",
            "column": "SiPM_Strip_ID",
            "default": None,
        },
        # "External ID":
        # {
        #     KW_TYPE: "string",
        #     "column": ("External ID", "External_ID", "Part ID", "Part_ID"), 
        # },

        ## For "Item" type only
        # "Institution": 186
        # "Country": "US",
        # "Manufacturer": "??", # Name? ID? 
        # "Comments": "",
        # "Subcomponents": {},
        # "Specifications": {},
        # "Enabled": True, # defaults to True

        ## For "Test" type only
        #"Comments": "",
        "Test Results":
        {
            # implied that this is a type "group" and these are the members
            # there are no keys, except possibly the SN/EID might be considered one

            "SiPM_Strip_ID": "string",
            "Content Manager":
            {
                KW_TYPE: "string",
                "value": "HWDB Python Utility",
            },
            "Contents":
            {
                KW_TYPE: "group",
                KW_KEY: ["Date", "Location"],
                KW_MEMBERS:
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
                    "(SiPM Location)":
                    {
                        KW_TYPE: "group",
                        KW_KEY: ["SiPM_Location"],
                        KW_MEMBERS:
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
    }
}
#}}}

class Test__Encoder(unittest.TestCase):
    #{{{
    """Test functionality within the Encoder module"""

    #-----------------------------------------------------------------------------
    
    @unittest.skip("not right now")    
    def test__preserve_order(self):
        #{{{
        """Test preserve/restore order functions"""

        original = \
        [
            "abc",
            "123",
            [ 10, 9, 8, 
                {"a": 1, "b": 2, 
                    "_meta": {"something": "else"}, 
                "c": 3}, 
            7],
            {
                "1": "abc",
                "2": [ 100, 99, 101],
                "3": {"c": 3, "d": 4},
            }
        ]


        # Note: we need to deepcopy because all of these functions
        # do an "in-place" reordering, and we want to be able to 
        # compare each step.
        preserved = Encoder.Encoder.preserve_order(deepcopy(original))
        scrambled = Encoder.Encoder.scramble_order(deepcopy(preserved))
        restored = Encoder.Encoder.restore_order(deepcopy(scrambled))

        # "preserved" and "scrambled" should be equal in content, but 
        # we should check the  json output to prove the ordering is different.
        self.assertNotEqual(json.dumps(preserved), json.dumps(scrambled), 
                        "scrambling did not appear to change the order")

        # "original" and "restored" should be identical
        self.assertEqual(json.dumps(original), json.dumps(restored))
        #}}}

    #-----------------------------------------------------------------------------
    
    @unittest.skip("not right now")    
    def test__encode(self):
        #{{{
        sheet_info = \
        {
            "Record Type": "Test",
            "Source": "Encoder Test",
            "File": "Dark-noise-SiPM-counts-truncated.xlsx",
            #"File": "Dark-noise-SiPM-counts.xlsx",
            "File Type": "Excel",
            "Sheet": "Sheet1",
            "Values":
            {
                "Part Type Name": "Z.Sandbox.HWDBUnitTest.snork",
            },
        }

        sheet = SheetReader.Sheet(sheet_info)

        #print(sheet.dataframe)

        encoder = Encoder.Encoder(encoder_DNSC)

        result1_deindexed = encoder.encode(sheet)

        result2_indexed = encoder.encode_indexed(sheet)
        result2_deindexed = encoder.deindex(result2_indexed)

        self.assertListEqual(result1_deindexed, result2_deindexed)

        result3_indexed = encoder.index(result2_deindexed)
        result3_deindexed = encoder.deindex(result3_indexed)
        self.assertListEqual(result2_deindexed, result3_deindexed)

        #printcolor(0xff7733, result1_deindexed)
        #printcolor(0x7777ff, result2_indexed)
        #printcolor(0x77ffff, result2_deindexed)
        #printcolor(0xff77ff, result3_deindexed)


        #print(json.dumps(result1, indent=4))
        #print(result)
        #}}}
   
    #-----------------------------------------------------------------------------
    
    #@unittest.skip("not right now")    
    def test__decode(self):
        #{{{
        sheet_info = \
        {
            "Record Type": "Test",
            "Source": "Encoder Test",
            "File": "Dark-noise-SiPM-counts-truncated.xlsx",
            #"File": "Dark-noise-SiPM-counts.xlsx",
            "File Type": "Excel",
            "Sheet": "Sheet1",
            "Values":
            {
                "Part Type Name": "Z.Sandbox.HWDBUnitTest.snork",
            },
        }

        sheet = SheetReader.Sheet(sheet_info)

        encoder = Encoder.Encoder(encoder_DNSC)

        result1 = encoder.encode(sheet)
        

        new_sheet = encoder.decode(result1)
        
        print() 
        printcolor(0xffaa00, new_sheet) 


        #}}}
   
    #-----------------------------------------------------------------------------

    @unittest.skip("not right now")
    def test__preprocess_schema(self):
        #{{{

        encoder_def = \
        {
            "Encoder Name": "Dark Noise SiPM Counts",
            "Record Type": "Test",
            "Part Type Name": "Z.Sandbox.HWDBUnitTest.snork",
            #"Part Type ID": "Z00100300022",
            "Test Name": "Dark Noise SiPM Counts",

            "Schema":
            {
                "Serial Number": "string",
                "Test Results":
                {
                    "Contents":
                    {
                        KW_TYPE: "group",
                        KW_KEY: ["Test ID"],
                        KW_MEMBERS:
                        {
                            "Test ID": "string",
                            "Date": "string",
                            "Temperature": "string",
                            "Humidity": "string"
                        },
                    }
                }
            }
        }

        encoder = Encoder.Encoder(encoder_def)

        #}}}
    
    #-----------------------------------------------------------------------------
   
    @unittest.skip("not right now")
    def test__merge_records(self):
        #{{{

        #{{{
        encoder_def = \
        {
            "Encoder Name": "Unit Test",
            "Record Type": "Test",
            "Part Type Name": "<for unit test only>",
            "Part Type ID": "<for unit test only",
            "Test Name": "Unit Test",

            "Schema":
            {
                "Extenal ID": "string",
                "Serial Number": "string",
                "Test Results":
                {
                    "Contents":
                    {
                        KW_TYPE: "group",
                        KW_KEY: ["Test ID"],
                        KW_MEMBERS:
                        {
                            "Test ID": "string",
                            "Date": "string",
                            "Temperature": "string",
                            "Humidity": "string",
                            "Status": "string",
                        },
                    }
                }
            }
        }
        
        encoder = Encoder.Encoder(encoder_def)
        #print(json.dumps(encoder.schema, indent=4))

        record = \
        {
            'Serial Number': 171, 
            'External ID': None, 
            'Test Comments': None, 
            'Test Results': 
            {
                '()':
                {
                    'Contents':
                    {
                        "('A001',)":
                        {
                            'Test ID': 'A001',
                            'Date': '2023-12-31',
                            'Temperature': '290K',
                            'Humidity': '30%',
                            'Status': 'PASS'
                        }
                    }
                }
            }
        }
 
        addendum = \
        {
            'Serial Number': 171, 
            'External ID': None, 
            'Test Comments': None, 
            'Test Results': 
            {
                '()':
                {
                    'Contents':
                    {
                        "('A002',)":
                        {
                            'Test ID': 'A002',
                            'Date': '2024-01-01',
                            'Temperature': '73K',
                            'Humidity': '0%',
                            'Status': 'FAIL'
                        }
                    }
                }
            }
        }
        #}}}

        result = encoder.merge_records(record, addendum)
        print()
        print(json.dumps(result, indent=4))



        
        



        #}}}

    #-----------------------------------------------------------------------------
    #}}}

#=================================================================================

if __name__ == "__main__":
    unittest.main(argv=config.remaining_args)   

