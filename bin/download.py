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

#-----------------------------------------------------------------------------

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
            ('--part-id',),
            {"metavar": "<part-id>", 'nargs': 1, 'action': 'append', 'required': True,
                'help': "Part ID of the item to download"}
        ),
    ]

    for args, kwargs in arg_table:
        group.add_argument(*args, **kwargs)

    args = parser.parse_known_args(command_line_args)
    return args
    #}}}

#-----------------------------------------------------------------------------

def main():
    logger.info(f"Starting {__name__}")
    Sisyphus.display_header() 

    args, unknowns = parse()


    logger.info(f"Finished {__name__} and exiting.")

#-----------------------------------------------------------------------------

if __name__ == '__main__':    
    sys.exit(main())

