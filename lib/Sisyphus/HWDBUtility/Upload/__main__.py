#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""
import os
import sys
import json
import Sisyphus
from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.HWDBUtility.Upload import Uploader
from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus import RestApiV1 as ra
from shutil import get_terminal_size


def main(argv=None):
    logger.info(f"Starting {__name__}")
    print('\n'*get_terminal_size()[1], end='')
    print(f'\x1b[{get_terminal_size()[1]}F', end='')
    #print(f"\x1b[{get_terminal_size()[1]}B", end='')
    Sisyphus.display_header()
    print()
    Style.info.print("Processing upload request...")
    print()
    

    uploader = Uploader.fromCommandLine(argv or sys.argv)

    docket = uploader.docket
   
    #Style.notice.print("Combined Docket:") 
    #Style.info.print(docket)

    logger.info(f"Finished {__name__} and exiting.")

if __name__ == "__main__":
    main(argv=config.remaining_args)
