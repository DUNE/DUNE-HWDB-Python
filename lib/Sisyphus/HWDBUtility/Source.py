#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/HWDBUtility/Source.py
Copyright (c) 2024 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.HWDBUtility.keywords import *

import Sisyphus.RestApiV1 as ra
import Sisyphus.RestApiV1.Utilities as ut

import json
import sys
import numpy as np
import pandas as pd
import os
from copy import deepcopy
import re
from glob import glob

pp = lambda s: print(json.dumps(s, indent=4))

class Source:
    def __init__(self, dkt, source_item):
        pass

    @classmethod
    def fromDocket(cls, dkt):
        #{{{
        logger.info("Parsing sources")
        if DKT_SOURCES not in dkt.keys():
            logger.warning(f"Docket '{dkt[DKT_DOCKET_NAME]}' has no '{DKT_SOURCES}' node")
            return

        # Grab the sources node. It should be a list, but it is allowed to be                                       # a single item if there's only one item. In that case, grab it and
        # put it in a list so that it can be handled the same ways lists are.
        sources = dkt[DKT_SOURCES]
        if type(sources) != list:
            sources = dkt[DKT_SOURCES]
                                                                                                                    # Create a base node containing information from the docket that should be carried
        # to all source manifest nodes.
        base = {
            "Docket Name": dkt[DKT_DOCKET_NAME],
            "Values": self.values,
        }

        source_manifest = []

        for source_node_index, source_node in enumerate(sources):
            if DKT_SOURCE_NAME not in source_node.keys():
                source_item[DKT_SOURCE_NAME] = "Unnamed Source Node {source_node_index}"

            source_manifest.extend(Source.fromSourceNode(base, source_node))

            #m = Source(dkt, source_item)

            sys.exit()

            #self._parse_source(dkt, source_item)

        #}}}



    @classmethod
    def fromSourceNode(cls, source_item):

        logger.warning("NEW parsing source")
        # Process a source node from a docket
        # A source node may have one or more files, each of which may have one
        # or more sheets. Create a manifest that lists each sheet individually,
        # and how to process each sheet. Some information may need to be obtained
        # from the sheet itself.

        self.manifest = manifest = []

        # The source should be a dictionary, but it is allowed to be a string.
        # If it's a string, put it in a dictionary under "File Name" and use
        # that dictionary instead.
        if type(source_item) == str:
            source_item = {DKT_FILES: source_item}
        if type(source_item) != dict:
            raise ValueError(f"Objects in '{DKT_SOURCE}' node must be strings or dictionaries")

        # Accumulate the 'refined' source node data here
        src = {
            # We are potentially accumulating from several dockets,
            # so record which docket this source came from
            DKT_DOCKET_NAME: dkt[DKT_DOCKET_NAME],

            DKT_SOURCE_NAME: source_item[DKT_SOURCE_NAME],
        }

        # The source node MUST have a filename.
        if DKT_FILES not in source_item:
            msg = (
                f"""Source Node "{source_item[DKT_SOURCE_NAME]} must have a """
                """'{DKT_FILES}' node."""
            )
            raise ValueError(msg)

        # The filename could actually be a list, so promote a single item to
        # a list and handle it that way. (Though, I suspect it'll usually just
        # be a single item.)
        filenames = source_item[DKT_FILES]
        if type(filenames) == str:
            filenames = [ filenames ]

        # Let's find all the files that match the items in filename, using glob
        # rules.
        files = []
        for filename in filenames:
            #globbed = [ os.path.abspath(fn)
            #                for fn in glob(os.path.expanduser(filename)) ]
            globbed = glob(os.path.expanduser(filename))
            files.extend(globbed)
        if len(files) == 0:
            msg = (f"Warning: file patterns in source '{src[DKT_SOURCE_NAME]}' in "
                    f"docket '{src[DKT_DOCKET_NAME]}' doesn't match any files.")
            logger.warning(msg)
            print(msg)
        
        pt_info = self.resolve_part_type(
                        source_item.get(DKT_PART_TYPE_ID, None),
                        source_item.get(DKT_PART_TYPE_NAME, None))
        if pt_info is not None:
            pt_id, pt_name = pt_info
        else:
            pt_id, pt_name = None, None

        # Grab the values attached at the source node level, if any.
        values = source_item.get(DKT_VALUES, {})

        # Check for an encoder at the source node level
        # (Note that there can be one at the sheet level that overrides this)
        encoder_name = source_item.get(DKT_ENCODER, None)
        #if encoder_name is None:
        #    encoder_name = DKT_AUTO

        # Check for a data type (e.g., item, test, image list)
        sheet_type = source_item.get(DKT_SHEET_TYPE, None)
        #if sheet_type is None:
        #    sheet_type = DKT_UNKNOWN








    @classmethod
    def _resolve_part_type(cls, part_type_id, part_type_name):
        if part_type_name is not None:
            pt_id, pt_name = ut.lookup_part_type_id_by_fullname(part_type_name)
            if part_type_id is not None and part_type_id != pt_id:
                raise ValueError("Type ID and Type Name do not match!")
            return pt_id, pt_name
        elif part_type_id is not None:
            ctdef = ut.lookup_component_type_defs(part_type_id)
            pt_id, pt_name = ctdef["part_type_id"], ctdef["full_name"]
            return pt_id, pt_name
        else:
            return None




















