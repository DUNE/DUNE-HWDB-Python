#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/upload-encoder.py
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

import sys
import argparse
import Sisyphus
import Sisyphus.Configuration as Config
from Sisyphus.Configuration import config
logger = config.getLogger(f"Sisyphus.{__name__}")
import Sisyphus.RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut

from Sisyphus.HWDBUtility.Encoder import Encoder
from Sisyphus.HWDBUtility.exceptions import *
from Sisyphus.Utils.Terminal import Image
from Sisyphus.Utils.Terminal.Style import Style

from Sisyphus.HWDBUtility.Docket import Docket
import json

def parse(command_line_args=sys.argv):
    #{{{
    parser = argparse.ArgumentParser(
        add_help=True,
        parents=[Config.config.arg_parser],
        #prefix_chars="-+",
        description=Style.notice('Uploads encoder information into the HWDB'))

    group = parser.add_argument_group(Style.notice('Upload Encoder Options'))
        
    arg_table = [
        (
            ('files',),
            {"metavar": "<docket-file>", 'nargs': '*', "default": None,
                'help': "Output docket file to insert downloaded encoder"}
        ),
        (
            ('--item-encoder',),
            {"metavar": "<part-type>", 
                'action': 'append',
                'help': "(TBD) Download the Item Encoder for the given part type"}
        ),
        (
            ('--test-encoder',),
            {'metavar': ("<part-type>", "<test-name>"),
                'nargs': 2, 'action': 'append',
                'help': '(TBD) Download the Test Encoder for the given part type and test name'
            }
        ),
        (
            ('--all-encoders',),
            {"metavar": "<part-type>", 
                'action': 'append',
                'help': "Download both the Item Encoder and all Test Encoders for the "
                        " given part type"}
        ),
    ]


    for args, kwargs in arg_table:
        group.add_argument(*args, **kwargs)


    args = parser.parse_known_args(command_line_args)
    return args
    #}}}z

def execute_request(args):

    filenames = args.files[1:]
    if filenames:
        filename = filenames[0]
    else:
        filename = "out.json"

    encoder_docket = {'Encoders': []}

    if args.all_encoders:
        #print(args.all_encoders)
        part_types = list(args.all_encoders)

        for part_type in part_types:
            if part_type.find('.') == -1:
                part_type_id = part_type
                part_type_name = None
            else:
                part_type_id = None
                part_type_name = part_type

            resp = ut.fetch_component_type(part_type_id=part_type_id, part_type_name=part_type_name)
            part_type_id = resp["ComponentType"]["part_type_id"]
            part_type_name = resp["ComponentType"]["full_name"]

            enc = Encoder.retrieve(record_type="Item", part_type_id=part_type_id)
            if enc is not None:
                encoder_docket['Encoders'].append(enc.encoder_def)

            test_names = [ node["name"] for node in resp["TestTypes"]]
            #print(test_names)

            for test_name in test_names:
                enc = Encoder.retrieve(record_type="Test", 
                                    part_type_id=part_type_id,
                                    test_name=test_name)
                #print(enc.encoder_def)
                if enc is not None:
                    encoder_docket['Encoders'].append(enc.encoder_def)

            #print(json.dumps(resp, indent=4))

    with open(filename, 'w') as f:
        f.write(json.dumps(encoder_docket, indent=4))



def main():
    logger.info(f"Starting {__name__}")
    Sisyphus.display_header() 

    args, unknowns = parse()

    execute_request(args)

    logger.info(f"Finished {__name__} and exiting.")

if __name__ == '__main__':    
    sys.exit(main())

