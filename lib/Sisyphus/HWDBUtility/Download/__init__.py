#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

import sys, os
import shutil
import json
import argparse
#from datetime import datetime, timezone
from copy import deepcopy

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus.HWDBUtility.Docket import Docket
from Sisyphus.HWDBUtility.SheetWriter import ExcelWriter
from Sisyphus.HWDBUtility.PDFLabels import PDFLabels

from Sisyphus.DataModel import HWItem
from Sisyphus.DataModel import HWTest

from Sisyphus.Utils.utils import preserve_order, restore_order, serialize_for_display
from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus.Utils.Terminal.BoxDraw import Table
from Sisyphus.Utils.Terminal import BoxDraw

from datetime import datetime

class Downloader():

    def __init__(self, args=None):
        #{{{                                                                                                    
        self.upload_time = datetime.now().astimezone().replace(microsecond=0)
        self.output_path = self.upload_time.replace(tzinfo=None).strftime('%Y%m%dT%H%M%S')

        try:
            os.unlink("latest")
        except:
            pass

        try:
            os.symlink(self.output_path, "latest", target_is_directory=True)
        except:
            logger.warning("Error creating symlink")
            pass

        #}}}


    #--------------------------------------------------------------------------


    @classmethod
    def fromCommandLine(self, argv=None):
        #{{{
        # Since we're probably not being invoked directly, we let the
        # calling script tell us what its name is, so we can adjust
        # our "help" screen accordingly.

        argv = argv or sys.argv
        prog_parser = argparse.ArgumentParser(add_help=False)
        prog_parser.add_argument('--progname')
        prog_args, argv = prog_parser.parse_known_args(argv)
        progname = prog_args.progname
        if progname is not None:
            progname = os.path.basename(progname)
            _ = argv.pop(0)
        else:
            progname = os.path.basename(argv.pop(0))

        description = "HWDB Download Utility"

        arg_table = [
            (
                ('files',),
                {"metavar": "file", 'nargs': '*', "default": None}
            ),
            (
                ('--part-id',),
                {'metavar': "<part-id>", 'nargs': 1, 'action': 'append'}
            ),
        ]

        parser = argparse.ArgumentParser(
                    prog=progname,
                    description=description,
                    add_help=True)

        for args, kwargs in arg_table:
            parser.add_argument(*args, **kwargs)

        args = parser.parse_args(argv)

        return Downloader(args)
        #}}}


