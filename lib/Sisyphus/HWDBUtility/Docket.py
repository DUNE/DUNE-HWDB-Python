#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/HWDBUtility/Docket.py
Copyright (c) 2024 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy

"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.HWDBUtility.keywords import *
from Sisyphus.HWDBUtility.Encoder import Encoder
from Sisyphus.HWDBUtility.SheetReader import Sheet
from Sisyphus.HWDBUtility.Source import Source

import Sisyphus.RestApiV1 as ra
from Sisyphus.RestApiV1.keywords import *
import Sisyphus.RestApiV1.Utilities as ut

from Sisyphus.Utils.Terminal.Style import Style

import json, json5
import sys
import numpy as np
import pandas as pd
from glob import glob
import os
from copy import deepcopy
import re
from uuid import uuid4

class Docket:
    #{{{
    def __init__(self, *, definition=None, filename=None, encoders_only=False):
        #{{{

        self.warnings = []
        self.errors = []
        
        if (definition and filename):
            raise ValueError("Must provide either a definition or a filename, but not both")
        if not (definition or filename):
            raise ValueError("Must provide a definition or a filename")

        if filename:
            #Style.info.print(f"Creating Docket from filename '{filename}'")

            suffix = filename.split('.')[-1].casefold()
            with open(filename, "r") as fp:
                raw_data = fp.read()
            
            if suffix in ("json", "json5"):
                try:
                    definition = json.loads(raw_data)
                except json.JSONDecodeError as exc:
                    try:
                        definition = json5.loads(raw_data)
                    except ValueError as exc2:
                        raise ValueError(f"Could not parse docket file "
                                                f"'{filename}'.", exc2) from None
            elif suffix in ("py",):
                try:
                    _locals, _globals = {}, {}
                    exec(raw_data, _globals, _locals)
                    definition = _locals["contents"]
                except Exception as exc: 
                    # you really can't predict what kind of exception "exec" will raise!
                    raise ValueError(f"Could not process docket file '{filename}'", exc) from None
            else:
                raise ValueError(f"Unrecognized docket file type: '{suffix}'")
        else:
            #Style.info.print(f"Creating Docket from definition")
            pass

        self._raw = definition
        self.docket_name = casefold_get(self._raw, "Docket Name", (filename or "unnamed"))
        self._preprocess_encoders()
        if not encoders_only: 
            self._preprocess_values()
            self._preprocess_sources()
            self._preprocess_includes() 
 
        #}}}
    
    #--------------------------------------------------------------------------

    def load_sheets(self):
        #{{{
        #Style.notice.print("(Docket) Loading Sheets...")

        self.sheets = []
        
        # Load all sheets
        for source in self.sources:
            #Style.info.print(json.dumps(source, indent=4))
            trace = (f"Docket '{source['_docket_name']}', "
                    f"Source '{source['Source Name']}', "
                    f"File '{source['Files'][0]}'")
            if 'Sheet Name' in source:
                trace += f", Sheet '{source['Sheet Name']}'"

            #msg = [f"Loading '{source['Files'][0]}'"]
            #if 'Sheet Name' in source:
            #    msg.append(f"'{source['Sheet Name']}'")
            #Style.notice.print("|".join(msg))

            if 'Sheet Name' in source:
                sheet_description = f"{source['Files'][0]} | {source['Sheet Name']}"
            else:    
                sheet_description = f"{source['Files'][0]}"

            Style.info.print(f"    \u2022 Loading {sheet_description}")
            
            #Style.warning.print(json.dumps(source, indent=4))
            aggregate, conflicts = merge_dict(self.values, source.get('Values', {}))

            try:
                sheet_obj = Sheet(
                            filename=source['Files'][0],
                            sheet=source.get('Sheet Name', None),
                            values=aggregate,
                            trace=trace)
            except ValueError:
                raise ValueError(f"Sheet not found: {trace}") from None

            self.sheets.append(
            {
                "Source": source,
                "Sheet": sheet_obj
            })
        #}}}
    
    #--------------------------------------------------------------------------

    def verify_encoders(self):
        #{{{
        # Check if each sheet's encoder can be found (or created if _AUTO_)
        #Style.debug.print("Checking sheets for encoders")
        
        logger.info(self.sheets)
        for sheet_node in self.sheets:
            sheet = sheet_node["Sheet"]
            source = sheet_node["Source"]
            #filename = source["Files"][0]
            #values = source["Values"]
            encoder_name = source["Encoder"]
            #sheet_name = source.get("Sheet Name", None)

            # The encoder could have been specified in the sheet itself, so
            # check for that. TODO: if the encoder in the Source is not _AUTO_,
            # having an encoder in the sheet is an error.

            if encoder_name == '_AUTO_':
                if (tmp:=sheet.coalesce(["Encoder"]).value) is not None:
                    encoder_name = tmp

            if encoder_name == '_AUTO_':
                params = \
                {
                    "record_type": sheet.coalesce(["Record Type"]).value,
                    "part_type_id": sheet.coalesce(["Part Type ID"]).value,
                    "part_type_name": sheet.coalesce(["Part Type Name"]).value,
                    "test_name": sheet.coalesce(["Test Name"]).value,
                }

                auto_encoder = Encoder.create_auto_encoder(**params)
            
                encoder_name = auto_encoder["Encoder Name"]    
                source["Encoder"] = encoder_name
    
                self.encoders[encoder_name] = auto_encoder


                #Style.error.print(json.dumps(auto_encoder, indent=4))
            else:
                #Style.error.print(f"We will use {encoder_name}")
                if encoder_name not in self.encoders:
                    raise ValueError(f"Cannot find encoder '{encoder_name}'")

            sheet_node["Encoder"] = Encoder(encoder_def=self.encoders[source["Encoder"]])
            #Style.warning.print(sheet_node)
        #}}}

    #--------------------------------------------------------------------------
    
    def apply_encoders(self):
        #{{{
        jobs = []
        for sheet_node in self.sheets:
            #Style.info.print("applying encoder to sheet")
            
            encoder = sheet_node["Encoder"]
            sheet = sheet_node["Sheet"]

            job_template = \
            {
                "Record Type": encoder.record_type,
                "Part Type ID": encoder.part_type_id,
                "Part Type Name": encoder.part_type_name,
                "Encoder": encoder,
            }
            if encoder.record_type in ("Test", "Test Image"):
                job_template["Test Name"] = encoder.test_name


            #Style.notice.print(json.dumps(encoder.schema, indent=4))

            job_list = encoder.encode(sheet)

            for job_unit in job_list:
                job = deepcopy(job_template)
                job["Data"] = job_unit
                jobs.append(job)
                #Style.error.print(json.dumps(job, indent=4))
        
        return jobs
        #}}}


    #--------------------------------------------------------------------------
 
    def _preprocess_sources(self):
        #{{{
        # From self.docket_def, take the source node and break it into 
        # bite-sized pieces with a consistent interface.

        # ..............

        def _preprocess_source(src_node):
            #{{{            
            # If it's just a string, replace it with a dict that only contains
            # that string as "Files", then continue processing it as normal
            if isinstance(src_node, str):
                src_node = {"Files": [src_node]}
            
            # We should now only have dictionaries to worry about.
            if not isinstance(src_node, dict):
                raise ValueError("Objects in 'Sources' node must be strings or dictionaries")
                
            src_node = {
                    "_docket_name": self.docket_name,
                    "Source Name": casefold_get(src_node, "Source Name", None),
                    **src_node
                }

            # Get "Files" and normalize to a list
            files = casefold_get(src_node, ("Files", "File"), None)

            if files is None:
                src_node["Files"] = None
                ... # This might be okay. Maybe the "source" is actually a full
                    # record, and we should allow it.
            else:
                if isinstance(files, str):
                    src_node["Files"] = [files]
                elif isinstance(files, (list, tuple)):
                    src_node["Files"] = list(files) # prob would have been fine as a tuple
                else:
                    raise ValueError("'Files' node must be a string or a list of strings")

            # What we have at this point might represent more than one 'source',
            # not just because the list might have more than one filename in it,
            # but because each filename might actually be a glob, and because
            # even when we've narrowed it down to one file, it could have sheets,
            # if it's an XLSX file.

            # Make the list (possibly) bigger by globbing each item in the list
            #Style.debug.print(f"before globbing: {src_node['Files']}")
            files = []
            for pattern in src_node["Files"]:
                files.extend(glob(os.path.expanduser(os.path.expandvars(pattern))))   
            src_node["Files"] = files
            #Style.debug.print(f"after globbing: {files}")
            if len(files) == 0:
                Style.warning.print(f"Warning: No matching files for source '{src_node['Source Name']}'")
                return
            if len(files) > 1:
                for filename in files:
                    src_copy = deepcopy(src_node)
                    src_copy["Files"] = [filename]
                    _preprocess_source(src_copy)
                return

            # We still need to split by "sheets," if there are any, but because
            # there could be "values" at both the "source" and "sheet" level, 
            # we should resolve "values" first.
            if (values := casefold_get(src_node, "Values",{})) is None:
                src_node["Values"] = {}
            if not (encoder := casefold_get(src_node, "Encoder", None)):
                src_node["Encoder"] = encoder = "_AUTO_"
            sheets = casefold_get(src_node, "Sheets", None, pop=True)

            # If there are sheets, then
            #   (1) there can't be a "sheet name" at this level
            #   (2) we need to split this out into single sheets, and each
            #       of those copies actually *will* have a "sheet name" at
            #       this level.
            if sheets is not None:
                if casefold_get(src_node, "Sheet Name", None) is not None:
                    raise ValueError("A source node should not contain both 'Sheet Name' "
                                "and 'Sheets'.")

                src_copy = deepcopy(src_node)

                for sheet in sheets:
                    # If it's just a string, turn it into a dict
                    if isinstance(sheet, str):
                        sheet = {"Sheet Name": sheet}

                    # TODO: a lot more error checking here.
                    sheet_values, conflicts = merge_dict(values, casefold_get(sheet, "Values", {}))
                    if conflicts:
                        raise ValueError(f"Values for sheet conflict with Values for file")
                    sheet_name = casefold_get(sheet, "Sheet Name")
                    encoder = casefold_get(sheet, "Encoder", "_AUTO_")
                        
                    src_copy_copy = deepcopy(src_copy)
                    src_copy_copy["Sheet Name"] = sheet_name
                    src_copy_copy["Values"] = sheet_values
                    src_copy_copy["Encoder"] = encoder

                    #_preprocess_source(src_copy_copy)
                    self.sources.append(src_copy_copy)    

                return       
     
            # If we've gotten here, then we've teased it all down to a single
            # file and a single sheet. There's still the problem of if it's 
            # an XLSX file, and no sheets were specified, we still need to dig
            # in and get the sheets.

            filename = src_node['Files'][0]
            ext = filename.split('.')[-1].casefold()
            if ext == 'xlsx' and 'Sheet Name' not in src_node:
                excel_file = pd.ExcelFile(filename)
                for sheet_name in excel_file.sheet_names:
                    src_copy = deepcopy(src_node)
                    src_copy["Sheet Name"] = sheet_name
                    self.sources.append(src_copy)
                return

            self.sources.append(src_node)
            #}}}
        # ..............
        
        self.sources = []
        raw_sources = casefold_get(self._raw, ["Sources", "Source"], None)

        if raw_sources is None:
            self.sources = {}
            return

        # If raw_sources isn't a list, make it into a list, since that's
        # how we want it for the rest of the processing.
        elif not isinstance(raw_sources, (list, tuple)):
            raw_sources = [raw_sources]

        for src_node in raw_sources:
            _preprocess_source(src_node) 
        #}}}

    #--------------------------------------------------------------------------

    def _preprocess_encoders(self):
        #{{{
        self.encoders = {}

        raw_encoders = casefold_get(self._raw, ("Encoders", "Encoder"), None)
        
        if raw_encoders is not None:
            for raw_encoder in raw_encoders:
                err_msg_prepend = f"In Docket '{self.docket_name}'"
                encoder = deepcopy(raw_encoder)
                
                encoder['_docket_name'] = self.docket_name
                
                if not (encoder_name := casefold_get(encoder, "Encoder Name", None)):
                    encoder_name = str(uuid4())
                    #raise ValueError(f"{err_msg_prepend}: Encoders must have 'Encoder Name'")
                
                if encoder_name in self.encoders:
                    raise ValueError(f"{err_msg_prepend}: Duplicate Encoder Name '{encoder_name}'")
                
                err_msg_prepend += f", Encoder '{encoder_name}'"
                
                if not (encoder_rectype := casefold_get(encoder, "Record Type", None)):
                    raise ValueError(f"{err_msg_prepend}: Encoders must specify 'Record Type'")
                
                encoder_part_type_name = casefold_get(encoder, "Part Type Name", None)
                encoder_part_type_id = casefold_get(encoder, "Part Type ID", None)
                if not (encoder_part_type_name or encoder_part_type_id):
                    raise ValueError(f"{err_msg_prepend}: Encoders must specify "
                                "'Part Type Name' or 'Part Type ID'")
                
                if encoder_rectype.casefold() in ('test', 'test image'):
                    if not (encoder_test_name := casefold_get(encoder, "Test Name", None)):
                        raise ValueError(f"{err_msg_prepend}: Encoders for 'Record Type' = 'Test' "
                                "must have 'Test Name'")

                if (encoder_schema := casefold_get(encoder, "Schema", None)) is None:
                    raise ValueError(f"{err_msg_prepend}: Encoders must specify 'Schema'")

                self.encoders[encoder_name] = encoder
        #}}}
        
    #--------------------------------------------------------------------------

    def _preprocess_values(self):
        #{{{
        # TODO: Think about if there's anything here that needs to be checked
        self.values = deepcopy(casefold_get(self._raw, "Values", {}))


        #}}}

    #--------------------------------------------------------------------------
    
    def _preprocess_includes(self):
        #{{{
        #Style.debug.print("processing includes")
        self.includes = []

        for include in casefold_get(self._raw, ("Include", "Includes"), []):
            new_docket = Docket(filename=include)
            self.includes.append(new_docket)

        
        # Merge the new dockets into this one

        for include in self.includes:
            #Style.info.print(f"Merging docket '{include.docket_name}' "
            #            "into docket '{}'")

            # Merge Values (pretty straightforward)
            self.values, conflicts = merge_dict(self.values, include.values) 
            if conflicts:
                raise ValueError(f"Conflict in 'Values' between docket '{self.docket_name}' "
                        "and docket '{include.docket_name}'")

            # Merge Encoders
            # We do not allow two encoders with the same name.
            for key, encoder in include.encoders.items():
                if key in self.encoders:
                    raise ValueError(f"In Docket '{include.docket_name}': "
                                f"Duplicate Encoder Name '{encoder_name}'")
                else:
                    self.encoders[key] = encoder

            # Merge Sources
            # TODO: check that the same file+sheet doesn't appear twice with the 
            # same encoder. (A different encoder is fine!)
            for source in include.sources:
                self.sources.append(source)


        #}}}

    #--------------------------------------------------------------------------

    def __str__(self):
        #{{{
        combined = \
        {
            "Docket Name": self.docket_name,
            "Values": self.values,
            "Sources": self.sources,
            "Encoders": self.encoders,
        }
        #}}}
        return json.dumps(combined, indent=4)
 
    #--------------------------------------------------------------------------
    #}}} 

#==============================================================================

def merge_dict(augend, addend):
    #{{{
    '''merge addend into augend, noting any conflicts'''

    aggregate = deepcopy(augend)
    conflicts = {}
    for key, value in addend.items():
        if key in aggregate and aggregate[key] != value:
            conflicts[key] = (aggregate[key], value)
        aggregate[key] = value 
                
    return aggregate, conflicts
    #}}}
    
#------------------------------------------------------------------------------

def casefold_get(dct, key, default=None, *, pop=False):
    #{{{
    '''Get an item from a dictionary while ignoring case of key

    Works similarly to dict.get, but will treat the key as case-insensitive.
    Key can also be a list of keys, if you want to check for similarly-named
    keys that should be equivalent, e.g., "source" and "sources". Will raise
    an exception if it ends up with more than one match! (E.g., "SOURCE" and
    "source" can be two different keys, but they're identical when you
    disregard case.)

    *** Side Effect *** (intentional!)
    The matching key in 'dct' will be changed to match the case of the first
    key in 'key'. So if 'dct' has 'source' but the first key is 'Source', it
    will be moved to 'Source'.

    This is not implemented very efficiently! If you need to do this for
    larger dictionaries, perhaps implement a dict subclass.
    ''' # TODO: make efficient

    retval = default
    matching_keys = []
    
    if isinstance(key, (tuple, list)):
        canonical_key = key[0] # this is the 'preferred' name and casing for the key
        keys = list(dict.fromkeys(k.casefold() for k in key))
    else:
        canonical_key = key
        keys = [key.casefold()]

    for k in dct:
        if k.casefold() in keys:
            retval = dct[k]
            matching_keys.append(k)

    if len(matching_keys) > 1:
        raise ValueError(f"Dictionary has more than one qualifying matches "
                f"for key '{canonical_key}': {matching_keys}")
    elif len(matching_keys) == 1:
        if matching_keys[0] != canonical_key:
            dct[canonical_key] = dct.pop(matching_keys[0])
        if pop:
            dct.pop(canonical_key)

    return retval
    #}}}

#------------------------------------------------------------------------------


#==============================================================================

if __name__ == "__main__":
    pass

