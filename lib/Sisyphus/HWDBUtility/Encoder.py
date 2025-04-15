#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/HWDBUtility/Encoder.py
Copyright (c) 2024 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

import Sisyphus.RestApiV1 as ra
ra.session_kwargs['timeout'] = 10


import Sisyphus.RestApiV1.Utilities as ut
from Sisyphus.HWDBUtility.SheetReader import Sheet, Cell
from Sisyphus.HWDBUtility import TypeCheck as tc
from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus.Utils.CI_dict import CI_dict
from Sisyphus.Utils import utils

from Sisyphus.HWDBUtility.exceptions import *

import pprint
pp = pprint.PrettyPrinter(indent=4)
from Sisyphus.Utils.utils import preserve_order, restore_order, serialize_for_display
import json
import sys
import numpy as np
import pandas as pd
import os
from copy import deepcopy
import re
import time
import random
import uuid

KW_TYPE = "type"
KW_KEY = "key"
KW_COLUMN = "column"
KW_CHOICES = "choices"
KW_MEMBERS = "members"
KW_VALUE = "value"
KW_DEFAULT = "default"

#pp = lambda s: print(json.dumps(s, indent=4))

printcolor = lambda c, s: print(Style.fg(c)(s))

#{{{
# Schema fields correspond to the database fields for the record type
# (Item, Test, etc.) that this encoder handles. The Encoder's "Schema"
# doesn't need to specify these unless they need some special handling
# that's different than the defaults.

default_universal_fields = \
{
    "Part Type ID": {KW_TYPE:"null,string", KW_COLUMN:"Part Type ID", KW_DEFAULT:None},
    "Part Type Name": {KW_TYPE:"null,string", KW_COLUMN:"Part Type Name", KW_DEFAULT:None},
    "External ID": {KW_TYPE:"null,string", KW_COLUMN:["External ID","Part ID"], KW_DEFAULT:None},
    "Serial Number": {KW_TYPE:"null,string", KW_COLUMN:"Serial Number", KW_DEFAULT:None},
}

default_schema_fields_by_record_type = \
{
    "Item":
    {
        # for all record types:
        **default_universal_fields,

        # for record type 'Item':
        "Institution": {KW_TYPE:"null,string", KW_COLUMN:"Institution", KW_DEFAULT:None},
        "Institution ID": {KW_TYPE:"null,integer", KW_COLUMN:"Institution ID", KW_DEFAULT:None},
        "Institution Name": {KW_TYPE:"null,string", KW_COLUMN:"Institution Name", KW_DEFAULT:None},
        "Country": {KW_TYPE:"null,string", KW_COLUMN:"Country", KW_DEFAULT:None},
        "Country Code": {KW_TYPE:"null,string", KW_COLUMN:"Country Code", KW_DEFAULT:None},
        "Country Name": {KW_TYPE:"null,string", KW_COLUMN:"Country Name", KW_DEFAULT:None},
        "Manufacturer": {KW_TYPE:"null,string", KW_COLUMN:"Manufacturer", KW_DEFAULT:None},
        "Manufacturer ID": {KW_TYPE:"null,integer", KW_COLUMN:"Manufacturer ID", KW_DEFAULT:None},
        "Manufacturer Name": {KW_TYPE:"null,string", KW_COLUMN:"Manufacturer Name", KW_DEFAULT:None},
        "Comments": {KW_TYPE:"string", KW_COLUMN:"Comments", KW_DEFAULT:""}, # SEE NOTE!
        "Status": {KW_TYPE:"string", KW_COLUMN:"Status", KW_DEFAULT:"1"},
        "Subcomponents": {KW_TYPE:"collection", KW_MEMBERS: {}},
        "Specifications": {KW_TYPE:"datasheet", KW_MEMBERS: {}},
        "Location": {KW_TYPE:"null,string", KW_COLUMN:"Location", KW_DEFAULT:None},
        "Location ID": {KW_TYPE:"null,integer", KW_COLUMN:"Location ID", KW_DEFAULT:None},
        "Location Name": {KW_TYPE:"null,string", KW_COLUMN:"Location Name", KW_DEFAULT:None},
        #"Location Country": {KW_TYPE: "null,string", KW_COLUMN:"Location Country", KW_DEFAULT:None},
        #"Location Country Code": {KW_TYPE: "null,string", KW_COLUMN:"Location Country Code", KW_DEFAULT:None},
        #"Location Country Name": {KW_TYPE: "null,string", KW_COLUMN:"Location Country Name", KW_DEFAULT:None},
        "Location Comments": {KW_TYPE:"null,string", KW_COLUMN:"Location Comments", KW_DEFAULT:""},
        "Arrived": {KW_TYPE:"null,string", KW_COLUMN:["Arrived","Location Timestamp"], KW_DEFAULT:""},
    },
    "Test":
    {
        # for all record types:
        **default_universal_fields,

        # for record_type 'Test' or 'Test Image':
        "Test Name": {KW_TYPE:"null,string", KW_COLUMN:"Test Name", KW_DEFAULT:None},

        # for record type 'Test':
        "Comments": {KW_TYPE:"string", KW_COLUMN:"Comments", KW_DEFAULT:""},
        "Test Results": {KW_TYPE:"datasheet"},
    },
    #"Item Image":
    #{
    #    # for all record types:
    #    **default_universal_fields,
    #
    #    # for record_type 'Item Image' or 'Test Image':
    #    "Comments": {KW_TYPE:"string", KW_COLUMN:"Comments", KW_DEFAULT:""},
    #    "Image File": {KW_TYPE:"null,string", KW_COLUMN:"Image File", KW_DEFAULT:None},
    #    "Save As": {KW_TYPE:"null,string", KW_COLUMN:"Save As", KW_DEFAULT:None},
    #},
    "Item Image":
    {
        # for all record types:
        **default_universal_fields,

        "Images": {
            KW_TYPE: "group",
            KW_KEY: ["Image File", "Save As", "Comments"],
            KW_MEMBERS: { 
                "Comments": {KW_TYPE:"string", KW_COLUMN:"Comments", KW_DEFAULT:""},
                "Image File": {KW_TYPE:"null,string", KW_COLUMN:"Image File", KW_DEFAULT:None},
                "Save As": {KW_TYPE:"null,string", KW_COLUMN:"Save As", KW_DEFAULT:None},
            }
        }
    },
    "Test Image":
    {
        # for all record types:
        **default_universal_fields,

        # for record_type 'Test' or 'Test Image':
        "Test Name": {KW_TYPE:"null,string", KW_COLUMN:"Comments", KW_DEFAULT:None},

        # for record_type 'Item Image" or 'Test Image':
        "Comments": {KW_TYPE:"string", KW_COLUMN:"Comments", KW_DEFAULT:""},
        "Image File": {KW_TYPE:"null,string", KW_COLUMN:"File", KW_DEFAULT:None},
        "Save As": {KW_TYPE:"null,string", KW_COLUMN:"Save As", KW_DEFAULT:None},
    }
}
#}}}

class Encoder:
    _encoder_cache = {}

    record_types = {
        k.casefold(): k for k in default_schema_fields_by_record_type.keys()
    }

    encoder_fields = {
        k.casefold(): k for k in
        ["Encoder Name", "Record Type", "Part Type ID", 
            "Part Type Name", "Test Name", "Schema", "Version"]
    }


    def __init__(self, encoder_def):
        #{{{

        # 'normalize' the fields in encoder_def
        self.encoder_def = {}
        for k, v in encoder_def.items():
            self.encoder_def[Encoder.encoder_fields.get(k, k)] = v

        enc = deepcopy(self.encoder_def)
        
        self.name = enc.pop("Encoder Name", None)

        # validate the record type
        record_type = enc.pop("Record Type", None)
        self.record_type = Encoder.record_types.get(record_type, record_type)
        if self.record_type in Encoder.record_types.values():       
            self.default_schema_fields = default_schema_fields_by_record_type[self.record_type] 
        elif self.record_type is None:
            raise InvalidEncoder(f"Record Type is required")
        else:
            raise InvalidEncoder(f"Unsupported Record Type: {self.record_type}")
 
        # validate the part type
        part_type_name = enc.pop("Part Type Name", None)
        part_type_id = enc.pop("Part Type ID", None)

        try:
            resp = ut.fetch_component_type(part_type_id, part_type_name)
        except ra.MissingArguments as ex:
            raise InvalidEncoder("Encoder must specify part_type_id or part_type_name")
        except ra.NotFound as ex:
            raise InvalidEncoder("Part type or name not found")

        self.part_type_id = self.encoder_def["Part Type ID"] = resp["ComponentType"]["part_type_id"]
        self.part_type_name = self.encoder_def["Part Type Name"] = resp["ComponentType"]["full_name"]

        # validate test name
        test_name = enc.pop("Test Name", None)
        if self.record_type in ["Test", "Test Image"]:
            if not test_name:
                raise InvalidEncoder(f"Test Name is required when Record Type is Test or Test Image.")
            
            for tt in resp["TestTypes"]:
                if tt['name'].casefold() == test_name.casefold():
                    self.test_name = tt['name']
                    break
            else:
                self.test_name = test_name
                logger.warning(f"Test Type '{self.test_name}' for {self.part_type_id} "
                        "does not exist and will need to be added before using this encoder")
        else:
            if test_name:
                raise InvalidEncoder(f"Test Name is only allowed for Test or Test Image types")
            self.test_name = None

        # validate the schema
        self.raw_schema = enc.pop("Schema", {})
        self.schema = self._preprocess_schema(self.raw_schema)

        # TODO: more fields

        # there shouldn't be any fields left
        extra_fields = [ k for k in enc.keys() if not k.startswith('_') ]
            
        if extra_fields:
            logger.warning(f"Extra fields in encoder: {extra_fields}")

        #}}}

    #--------------------------------------------------------------------------

    def root_fields(self):
        "Returns what fields need to be in the spec, according to the encoder"
        #{{{

        if self.record_type.casefold() == "item":
            root = self.schema["members"]["Specifications"]["members"]
        elif self.record_type.casefold() == "test":
            root = self.schema["members"] ["Test Results"]["members"]
        else:
            return None

        fields = {}
        
        for k, v in root.items():
            if v["type"] == "group":
                fields[k] = {}
            else:
                if "value" in v:
                    fields[k] = v['value']
                else:
                    fields[k] = v.get("default", None)

        return fields
        #}}}

    #--------------------------------------------------------------------------

    def store(self, dryrun=False):
        '''Store this encoder in the HWDB'''

        #{{{
        # Only items and tests can be (or even need to be) stored
        if self.record_type not in ["Item", "Test"]:
            logger.warning(f"Cannot store encoders of type '{self.record_type}'")
            return
    
        # We don't need to catch errors here because we already know it exists.
        # It'll just pull from the cache anyway. We just want a copy.
        resp = ut.fetch_component_type(self.part_type_id, self.part_type_name)
        ct = resp["ComponentType"]
        if ct["properties"] is not None:
            spec = restore_order(ct["properties"]["specifications"][-1]["datasheet"])
            spec_version = ct["properties"]["specifications"][-1]["version"]
        else:
            spec = {}
            spec_version = -1
        naked_spec = {k: v for k, v in spec.items() if k !='_meta'}

        # The spec may not have been initialized before, so we need to add the
        # necessary structure
        spec.setdefault("_meta", {}).setdefault('encoders', {}).setdefault('Item', [])
        spec['_meta']['encoders'].setdefault('Test', {})
        if self.record_type == "Test":
            spec['_meta']['encoders']['Test'].setdefault(self.test_name, [])

        item_encoders = spec['_meta']['encoders']['Item']
        all_test_encoders = spec['_meta']['encoders']['Test']
        
        if self.record_type == 'Test':
            my_test_encoders = all_test_encoders[self.test_name]

        # Any existing encoders with version=None are actually the current version
        # number of this datasheet. The reason it is None now is because we couldn't 
        # know for absolute certain what the next version number would be. It's 
        # probably going to be the last version number incremented by one, but it's 
        # dangerous to rely on it. 

        for encoder in item_encoders:
            if encoder.get('version', None) is None:
                encoder['version'] = spec_version
            encoder['Schema'] = Encoder.preserve_schema_order(encoder['Schema'])
        for tn, encoder_list in all_test_encoders.items():
            for encoder in encoder_list:
                if encoder.get('version', None) is None:
                    encoder['version'] = spec_version
                encoder['Schema'] = Encoder.preserve_schema_order(encoder['Schema'])
                
        # Now we can insert our new encoder.
        # We should check to make sure it has actually changed, though.
        enc_def = {
            'Schema': Encoder.preserve_schema_order(self.raw_schema),
            'version': None
        }

        if self.record_type == "Item":
            prev_encoder = item_encoders[0]['Schema'] if item_encoders else None

            if prev_encoder == enc_def['Schema']:
                changed = False
            else:
                changed = True
                item_encoders.insert(0, enc_def)

            # We should check that the fields for this item spec match the fields
            # described in the encoder

            root_fields = self.root_fields()

            if naked_spec != root_fields:
                changed = True
                new_spec = preserve_order(root_fields)
                new_spec.setdefault("_meta", {}).update(spec['_meta'].items())
                spec = new_spec

                #logger.info(f"keys in spec: {naked_spec}")
                #logger.info(f"keys in encoder: {self.root_fields()}")


        else:
            prev_encoder = my_test_encoders[0]['Schema'] if my_test_encoders else None
            
            if prev_encoder == enc_def['Schema']:
                changed = False
            else:
                changed = True
                my_test_encoders.insert(0, enc_def)

        if not changed:
            logger.info("Encoder has not changed and will not be updated")
            return False

        #logger.info("Old version:")
        #logger.info(json.dumps(prev_encoder, indent=4))
        #logger.info("New version:")
        #logger.info(json.dumps(enc_def["Schema"], indent=4))


        # Upload the updated component type def
        data = {
            "comments": ct["comments"],
            "connectors": ct["connectors"],
            "manufacturers": [ s['id'] for s in ct["manufacturers"] ],
            "name": ct["full_name"],
            "part_type_id": ct["part_type_id"],
            "properties":
            {
                "specifications":
                {
                    "datasheet": spec,
                }
            },
            "roles": [ s['id'] for s in ct["roles"] ],
        }

        if dryrun:
            logger.info(f"Storing encoder (dry run only!): {json.dumps(data, indent=4)}")
        else:
            resp = ra.patch_component_type(self.part_type_id, data)
            logger.debug(f"Response from server: {json.dumps(resp, indent=4)}")

            # Just for safety, we should reload this part type, so no one will
            # get the outdated cached data for this.
            logger.debug(f"Reloading part type info for {self.part_type_id}")
            resp = ut.fetch_component_type(part_type_id=self.part_type_id, use_cache=False)

        return True
        #}}}

    #--------------------------------------------------------------------------

    @staticmethod
    def retrieve(record_type, part_type_id=None, part_type_name=None, test_name=None, version=None):
        '''Retrieve an encoder from the HWDB'''
        #{{{

        # Only items and tests can be (or even need to be) stored
        if record_type.casefold() == "item":
            record_type = 'Item'
        elif record_type.casefold() == "test":
            record_type = 'Test'
            if not test_name:
                raise InvalidEncoder("test_name is required if record_type is 'Test'")
        else:
            raise InvalidEncoder("record_type must be 'Item' or 'Test'")

        # Let's look up the part type
        try:
            resp = ut.fetch_component_type(part_type_id, part_type_name)
        except ra.MissingArguments as ex:
            raise InvalidEncoder("Encoder must specify part_type_id or part_type_name")
        except ra.NotFound as ex:
            raise InvalidEncoder("Part type or name not found")

        # Repopulate these values from the response, since it sort of 'normalizes' them
        part_type_id = resp["ComponentType"]["part_type_id"]
        part_type_name = resp["ComponentType"]["full_name"]

        ct = resp["ComponentType"]
        if ct["properties"] is not None:
            spec = restore_order(ct["properties"]["specifications"][-1]["datasheet"])
            spec_version = ct["properties"]["specifications"][-1]["version"]
        else:
            spec = {}
            spec_version = -1

        # The spec may not have been initialized before, so we need to add the
        # necessary structure. We won't be saving it, but it makes accessing it
        # easier
        spec.setdefault("_meta", {}).setdefault('encoders', {}).setdefault('Item', [])
        spec['_meta']['encoders'].setdefault('Test', {})

        item_encoders = spec['_meta']['encoders']['Item']
        all_test_encoders = spec['_meta']['encoders']['Test']
        
        if record_type == 'Test':
            for tn in all_test_encoders.keys():
                if tn.casefold() == test_name.casefold():
                    test_name = tn
                    my_test_encoders = all_test_encoders[test_name]
                    break
            else:
                # The test encoder does not exist. We can quit now.
                logger.warning(f"Part Type {part_type_id} does not have a test '{test_name}'")
                return None

            if version is None:
                if my_test_encoders:
                    test_encoder = my_test_encoders[0]
                    encoder_schema = test_encoder["Schema"]
                    encoder_version = test_encoder["version"] or spec_version
                else:
                    # There is no item encoder. We can quit.
                    logger.warning(f"Part Type {part_type_id}, Test Type '{test_name}' "
                        f"does not have an uploaded encoder")
                    return None
            else:
                for test_encoder in my_test_encoders:
                    if test_encoder["version"] == version:
                        encoder_schema = test_encoder["Schema"]
                        encoder_version = test_encoder["Version"]
                        break
                else:
                    # The specific version requested does not exist. We can quit.
                    logger.warning(f"Part Type {part_type_id}, Test Type '{test_name}' "
                        f"does not have a version '{version}'")
                    return None
            
            # At this point, we have an encoder schema, so we can construct the
            # encoder

            enc_name = f"_SAVED_{part_type_id}_{test_name.replace(' ', '_')}"
            enc_def = {
                "Encoder Name": enc_name,
                "Record Type": "Test",
                "Part Type Name": part_type_name,
                "Part Type ID": part_type_id,
                "Test Name": test_name,
                "Schema": encoder_schema,
                "Version": encoder_version,
            }
            return Encoder(enc_def)

        else: # Must be record_type=Item
            if version is None:
                if item_encoders:
                    item_encoder = item_encoders[0]
                    encoder_schema = item_encoder["Schema"]
                    encoder_version = item_encoder["version"] or spec_version
                else:
                    # The specific version requested does not exist. We can quit.
                    logger.warning(f"Part Type {part_type_id} does not have an "
                            f"uploaded encoder")
                    return None
                    
            else:
                for item_encoder in item_encoders:
                    if item_encoder["version"] == version:
                        encoder_schema = item_encoder["Schema"]
                        encoder_version = item_encoder["version"]
                        break
                else:
                    # The specific version requested does not exist. We can quit
                    logger.warning(f"Part Type {part_type_id} does not have a "
                            f"version '{version}'")
            
            # At this point, we have an encoder schema, so we can construct the
            # encoder

            enc_name = f"_SAVED_{part_type_id}"
            enc_def = {
                "Encoder Name": enc_name,
                "Record Type": "Item",
                "Part Type Name": part_type_name,
                "Part Type ID": part_type_id,
                "Schema": encoder_schema,
                "Version": encoder_version,
            }
            return Encoder(enc_def)
        #}}}            

    #--------------------------------------------------------------------------
    
    def _preprocess_schema(self, schema):
        #{{{
        """'Normalize' the schema to make encoding simpler

        * make the entire schema a 'schema' type (essentially, a group), and 
            all schema fields 'members' of this schema/group. The key for this
            schema/group is ('External ID', 'Serial Number')
        * insert the default fields for this record_type, if not already present
        * make all field definitions into dictionaries with the correct fields
            (user's field definitions are allowed to be a string containing the
            type, but convert it to a dict containing 'type'
        * any fields that are of type 'datasheet' (i.e., 'Specifications' and
            'Test Results') or 'collection' ('Subcomponents') should also be
            converted into 'datasheet' or 'collection' groups.
        """
        #......................................................................
        
        def make_prefix_variants(schema_key, column, prefix):

            # TODO: consider changing the order of what it looks for
            
            if column is None:
                columns = [schema_key]
            elif isinstance(column, (list, tuple)):
                columns = list(column) + [schema_key]
            else:
                columns = [column, schema_key]

            if prefix:
                prefixed = []
                naked = []
                for column in columns:
                    if column[:2].casefold() == prefix.casefold():
                        prefixed.append(column)
                        naked.append(column[2:])
                    else:
                        naked.append(column)
                        prefixed.append(prefix + column)
                columns = list(CI_dict.fromkeys(prefixed + naked).keys())
        
            # strip out duplicates
            columns = list({k: None for k in columns})
    
            return columns


        def preprocess_group(sch_in, sch_type=None):
            #{{{
            sch_in = deepcopy(sch_in)
            sch_out = {}

            field_prefix = None
            if self.record_type == "Item":
                if sch_type in ('datasheet', 'group'):
                    field_prefix = "S:"
                elif sch_type in ('collection',):
                    field_prefix = "C:"
            elif self.record_type == "Test":
                if sch_type in ('datasheet', 'group'):
                    field_prefix = "T:"

            for schema_key, field_def in sch_in.items():
                field_def = deepcopy(field_def)

                if type(field_def) is str:
                    sch_out[schema_key] = \
                    {
                        KW_TYPE: field_def,
                        KW_COLUMN: make_prefix_variants(schema_key, None, field_prefix),
                        KW_DEFAULT: None
                    }
                    continue

                # From here forward, "field_def" is assumed to be a dict

                node = sch_out[schema_key] = {KW_TYPE: field_def.get(KW_TYPE, "null,any")}
               
                # If this has a "value", then this is just a constant that doesn't
                # actually depend on what's in the sheet. 
                if KW_VALUE in field_def:
                    node[KW_VALUE] = field_def.pop(KW_VALUE)
                    # TODO: check if there are any leftover keys
                    continue

                if node[KW_TYPE] == "group":
                    key = field_def.pop(KW_KEY, []) 
                    if type(key) is list:
                        node[KW_KEY] = key
                    else:
                        node[KW_KEY] = [key]

                    members = field_def.pop(KW_MEMBERS, {})
                    node[KW_MEMBERS] = preprocess_group(members, "group")

                    # check that all the "key"s are in members
                    for key_name in node[KW_KEY]:
                        if key_name not in node[KW_MEMBERS]:
                            raise ValueError("Bad schema: key '{key_name}' not in members")

                    # TODO: check if there are any leftover keys
                    continue

                member_def = {**typedef_default, **field_def}
                columns = make_prefix_variants(schema_key, member_def['column'], field_prefix)
                member_def['column'] = columns

                sch_out[schema_key] = member_def

            return sch_out
            #}}}
        
        #......................................................................
        
        def has_groups(members):
            return (
                isinstance(members, dict)
                and any(
                    isinstance(v, dict) and v.get('type', None) in 
                            ('group', 'collection', 'datasheet', 'schema')
                    for v in members.values())
                )

        #......................................................................

        typedef_default = \
        {
            KW_TYPE: "null,any", 
            KW_COLUMN: None, 
            KW_DEFAULT: None,
        }

        sch_in = deepcopy(schema)
        if sch_in.get('type', None) == 'schema':
            # This is the 'spelled out' version of the schema, which should
            # be legal. But to handle it we need to go to the 'members' node,
            # which will look more like the ordinary unprocessed version
            sch_in = sch_in['members']

        sch_out = {}

        # Process the root level
        # We can only handle the fields listed in the 'default' schema, because
        # these correspond with what the database can hold for this record type.
        # TODO: Warn if extra fields are found
        # TODO: Create a mechanism to suppress this warning
        
        for schema_key, default_field_def in self.default_schema_fields.items():
        
            field_type = default_field_def[KW_TYPE]

            if field_type in ("datasheet", "collection"):
                if schema_key in sch_in:
                    user_field_def = sch_in[schema_key]
                    # If the user provided this (and they should!), we should check
                    # how they provided it. The usual case is that they gave it as
                    # a dictionary of fields, which consists of the "members" of 
                    # this datasheet (which is essentially the same as a group), 
                    # but they should be allowed to provide it in the same form
                    # as we will process it into, so check for 'type' and 'members'.

                    if user_field_def.get('type', None) in ("datasheet", "collection"):
                        # this is already in 'processed' form, so skip ahead to
                        # the 'members' node
                        user_field_def = user_field_def['members']                   

 
                    if isinstance(default_field_def, str):
                        # If it's a string instead of a dictionary, then the 
                        # string indicates the type, which is useless for a
                        # datasheet, because then there's no way of listing the
                        # members. But, let's go ahead and give them a datasheet
                        # with no members.
                        sch_out[schema_key] = \
                        {
                            KW_TYPE: field_type,
                            KW_MEMBERS: {},
                        }
                        continue
                    
                    if isinstance(default_field_def, list):
                        # If it's a list, it better be a list of strings, each
                        # of which is a name of a field of type 'any'.
                        assert(all(isinstance(s, str) for s in default_field_def))
                        sch_out[schema_key] = \
                        {
                            KW_TYPE: field_type,
                            KW_MEMBERS: {s:"any" for s in default_field_def},
                        }
                        continue
                    
                    if not isinstance(default_field_def, dict):
                        raise ValueError(f"{field_type} in schema must be a dictionary")
                    
                    if not {KW_TYPE, KW_MEMBERS, KW_KEY}.difference(default_field_def.keys()):
                        # The only fields here, if any at all, are 'type', 
                        # 'members', and 'key', so interpret this as a 
                        # fully-defined field definition and use it as-is. But
                        # the type (if present) has to be the correct field
                        # type, and the key (if present) has to be empty.
                        if user_field_def.get(KW_TYPE, field_type) != field_type:
                            raise ValueError("this schema field must be of type "
                                        f"'{field_type}'")
                        if not user_field_def.get(KW_KEY, None):
                            raise ValueError(f"{field_type} must not have 'key'")
                       
                        members = user_field_def.get(KW_MEMBERS, {})

                        if field_type == "collection":
                            if has_groups(members):
                                raise ValueError(f"{schema_key} may not have any subgroups")   
 
                        sch_out[schema_key] = \
                        {
                            KW_TYPE: field_type,
                            KW_MEMBERS: preprocess_group(members, field_type),
                        }
                        continue
                        
                    # None of the above apply.
                    # NOTE: this should be the most common case!
                    # Treat this dictionary as a list of members. (It might
                    # actually include the members 'type', 'members', and 
                    # 'key', as long as there's at least one more field. 
                    # (If something goes wrong because of it, then they get 
                    # what they deserve.) Since one of these members might
                    # be a group, we have to preprocess that node, too.
                    members = user_field_def
                    if field_type == "collection":
                        if has_groups(members):
                            raise ValueError(f"{schema_key} may not have any subgroups")   
                    
                    sch_out[schema_key] = \
                    {
                        KW_TYPE: field_type,
                        KW_MEMBERS: preprocess_group(members, field_type),
                    }
                    continue
                
                else:
                    # They didn't provide this field, so we'll just give them
                    # a datasheet with no members.
                    sch_out[schema_key] = default_field_def
                    continue
                logger.warning("This line should be unreachable. A 'continue' "
                        "is missing somewhere.")
                continue
           
            # If we got here, the field_type is just a normal field
            if schema_key in sch_in:
                user_field_def = sch_in[schema_key]
                if type(user_field_def) is str:
                    sch_out[schema_key] = {**default_field_def, KW_TYPE: user_field_def}
                elif KW_VALUE in user_field_def:
                    sch_out[schema_key] = {KW_TYPE: "null,any", **user_field_def}
                else:
                    sch_out[schema_key] = {**default_field_def, **user_field_def}
                
                if sch_out[schema_key].get(KW_COLUMN) is not None:
                    sch_out[schema_key][KW_COLUMN] = \
                                    make_prefix_variants(
                                        schema_key,
                                        sch_out[schema_key][KW_COLUMN],
                                        None)

                continue           
 
            # Use the default
            sch_out[schema_key] = deepcopy(default_field_def)
            
            if sch_out[schema_key].get(KW_COLUMN) is not None:
                sch_out[schema_key][KW_COLUMN] = make_prefix_variants(
                                                    schema_key,
                                                    sch_out[schema_key][KW_COLUMN],
                                                    None) 
        # Embed this in a schema type and return
        preprocessed_schema = \
        {
            KW_TYPE: "schema",
            KW_KEY: ["External ID", "Serial Number"],
            KW_MEMBERS: sch_out,
        }
        #Style.warning.print(json.dumps(preprocessed_schema, indent=4))
        return preprocessed_schema
        #}}}
    
    #--------------------------------------------------------------------------

    def index(self, record, schema=None):
        #{{{
        """Convert lists of row data into indexed dictionaries

        This makes it easier to locate rows so that information can be inserted.
        Since indexes may have more than one key, and JSON doesn't allow tuples
        to be keys, this format should be only used to manipulate data. It should
        be deindexed again before adding to the HWDB.
        
        Parameters:
            record: a list of dict, each dict represents a set of fields, where
                some subset of fields represents a key to identify that dict
            schema: the schema of an encoder, or a subnode in the schema that
                looks like a schema (mostly by having a 'members' node) 
        """
        
        record = deepcopy(record)
        if schema is None:
            schema = self.schema

        indexed = { tuple(v[k] for k in schema.get(KW_KEY, [])): v for v in record }

        for k, v in indexed.items():
            for member_key, member_def in schema['members'].items():
                if member_def[KW_TYPE] == "group":
                    v[member_key] = self.index(v[member_key], member_def)

        return indexed
        #}}}    

    #--------------------------------------------------------------------------        

    def deindex(self, record, schema=None):
        #{{{
        """Turn indexed rows back into lists"""

        record = deepcopy(record)
        if schema is None:
            schema = self.schema

        for k, v in record.items():
            for schema_key, field_def in schema[KW_MEMBERS].items():
                if field_def[KW_TYPE] in ("group", "schema", "datasheet", "collection"):
                    v[schema_key] = self.deindex(v[schema_key], field_def)
        
        return list(record.values())
        #}}}

    #-------------------------------------------------------------------------- 

    def merge_indexed_records(self, record, addendum, schema=None):
        #{{{
        """Merge two sets of row data when the rows are already indexed"""

        if schema is None:
            schema = self.schema

        #print("MIR")

        merged = {}
        
        for schema_key, field_def in schema[KW_MEMBERS].items():
            if field_def[KW_TYPE] in ("group", "schema", "datasheet", "collection"):
                merged[schema_key] = deepcopy(record[schema_key])
                for k, v in addendum[schema_key].items():
                    if k in record[schema_key]:
                        merged[schema_key][k] = self.merge_indexed_records(
                                                    record[schema_key][k], 
                                                    v,
                                                    field_def)
                    else:
                        merged[schema_key][k] = v
            else:
                #print(schema_key, field_def[KW_TYPE])
                #print(record)
                #if schema_key not in record:
                #    breakpoint()
                merged[schema_key] = record[schema_key]

        return merged
        #}}}

    #--------------------------------------------------------------------------

    def merge_records(self, record, addendum, schema=None):
        #{{{
        """Merge two sets of row data"""

        record_indexed = self.index(record, schema)
        addendum_indexed = self.index(addendum, schema)
        Style.fg(0x66ff00).print("OLD DATA:", 
                        json.dumps(serialize_for_display(record_indexed), indent=4))
        Style.fg(0x00ff00).print("NEW DATA:", 
                        json.dumps(serialize_for_display(addendum_indexed), indent=4))
        #breakpoint()

        '''
        #merged = deepcopy(record)
        merged = {}

        for key, addendum_value in addendum.items():
            if key in record:
                record_value = record[key]
                for schema_key, field_def in schema[KW_MEMBERS].items():
                    if field_def[KW_TYPE] in ("group", "schema", "datasheet", "collection"):
                        # if it's grouplike, we need to merge the two 
                        merged[key][schema_key] = self.merge_indexed_records(
                                    record_value[schema_key],
                                    addendum_value[schema_key],
                                    field_def)
                    else:
                        # if it's not grouplike, overwrite the 'record' copy with the 'addendum'
                        merged[key][schema_key] = addendum_value[schema_key]
                        
            else:
                merged[key] = addendum_value

        return merged
        '''

        merged_indexed = {}
        
        for key, addendum_value in addendum_indexed.items():
            merged_indexed[key] = {}
            if key in record_indexed:
                record_value = record_indexed[key]
                for schema_key, field_def in schema[KW_MEMBERS].items():
                    if field_def[KW_TYPE] in ("group", "schema", "datasheet", "collection"):
                        # if it's grouplike, we need to merge the two
                        merged_indexed[key][schema_key] = self.merge_indexed_records(
                                    record_value[schema_key],
                                    addendum_value[schema_key],
                                    field_def)
                    else:
                        # if it's not grouplike, overwrite the 'record' copy with the 'addendum'
                        merged_indexed[key][schema_key] = addendum_value[schema_key]

            else:
                merged_indexed[key] = addendum_value

        #merged_indexed = self.merge_indexed_records(record_indexed, addendum_indexed, schema)        

        merged = self.deindex(merged_indexed, schema)

        return merged
        #}}}

    #--------------------------------------------------------------------------

    def encode_indexed(self, sheet):
        #{{{
        """Encode a spreadsheet using the stored schema using indexed rows"""
        
        #......................................................................

        def encode_group(sheet, row_index, parent_field_def):
            #{{{ 
            group_value = {} 
 
            for schema_key, field_def in parent_field_def[KW_MEMBERS].items():
                
                if field_def[KW_TYPE] in ("group", "schema", "collection", "datasheet"):
                    k, v = encode_group(sheet, row_index, field_def)
                    group_value[schema_key] = {k: v} 
                    continue

                if KW_COLUMN in field_def:
                    columns = deepcopy(field_def[KW_COLUMN])
                    field_contents = sheet.coalesce(
                                columns, 
                                row_index, 
                                field_def[KW_TYPE],
                                field_def.get(KW_CHOICES)
                            )
                    if field_contents.location == "not found":
                        field_contents.value = field_def[KW_DEFAULT]
                elif KW_VALUE in field_def:
                    field_contents = Cell(  
                            source="encoder", 
                            location=None,
                            warnings=[], 
                            datatype=field_def[KW_TYPE],
                            value=field_def[KW_VALUE])
                
                # TODO: handle warnings
                if field_contents.warnings:
                    warnings = field_contents.warnings
                    location = field_contents.location
                    loc_col = location.column       
                    loc_row = location.row
                    
                    if loc_row == "header":
                        if loc_col not in header_warnings:
                            header_warnings[loc_col] = f"for field '{loc_col}': {warnings[-1]}"
                    elif loc_row == "inherited":
                        if loc_col not in global_warnings:
                            global_warnings[loc_col] = f"for field '{loc_col}': {warnings[-1]}"
                    else:
                        row_warnings.setdefault(loc_row, {})[loc_col] = warnings[-1]

                    #conversion_warnings.append(f"
                    #Style.warning.print("Conversion warning")
                    #Style.warning.print(field_contents)

                group_value[schema_key] = field_contents.value
            
            if parent_field_def[KW_TYPE] in ('collection', 'datasheet'):
                key = ()
            else:
                key = tuple( group_value[key] for key in parent_field_def[KW_KEY])
            
            return key, group_value
            #}}}
        #......................................................................

        sheet.local_values["Test Name"] = self.test_name

        result = {}
        header_warnings = {}
        global_warnings = {}
        row_warnings = {} 

        Style.info.print(f"    \u2022 Encoding sheet '{sheet.description()}' with encoder '{self.name}'")
        print()

        for row_index in range(sheet.rows):
            print(f"\x1b[1F        Processing row {row_index+1} of {sheet.rows}\x1b[K")
            key, group_value = encode_group(sheet, row_index, self.schema)

            if key not in result:
                result[key] = group_value
            else:
                result[key] = self.merge_indexed_records(result[key], group_value)
            
        print(f"\x1b[1F        {len(result)} records found in {sheet.rows} rows\x1b[K")

        if global_warnings:
            Style.warning.print("        The following warnings occurred with the values passed to the sheet:")
            for loc_col, msg in global_warnings.items():
                Style.warning.print(f"            \u2022 {msg}")
        if header_warnings:
            Style.warning.print("        The following warnings occurred in the header of the sheet:")
            for loc_col, msg in header_warnings.items():
                Style.warning.print(f"            \u2022 {msg}")
        if row_warnings:
            Style.warning.print("        The following warnings occurred in the main body of the sheet:")
            for loc_row, row_info in row_warnings.items():
                for loc_col, msg in row_info.items():
                    Style.warning.print(f"            \u2022 in row {loc_row}, field '{loc_col}': {msg}")


        return result
        #}}}    

    #--------------------------------------------------------------------------

    def encode(self, sheet):
        #{{{
        """Encode a spreadsheet using the stored schema"""

        #logger.info(json.dumps(self.schema, indent=4))

        encoded_data = self.encode_indexed(sheet)
        deindexed = self.deindex(encoded_data)
        
        return deindexed
        #}}}
    #--------------------------------------------------------------------------

    def decode(self, record):
        #{{{
        
        def make_row_template(schema):
            template = {}
            for schema_key, field_def in schema["members"].items():
                field_type = field_def["type"]

                if field_type == "group":
                    #print("GROUP")
                    template.update(make_row_template(field_def))
                elif field_type == "datasheet":
                    #print("DATASHEET")
                    template.update(make_row_template(field_def))
                elif field_type == "collection":
                    #print("COLLECTION")
                    template.update(make_row_template(field_def))
                elif field_type == "schema":
                    template.update(make_row_template(field_def))
                else:
                    template[schema_key] = field_def

            return template


        template = make_row_template(self.schema)

        def make_rows(record, schema, current_row):
            # Use 'schema' to locate fields in 'record' and put them in 'current_row'
            # when the field type is 'group', recursively call make_rows to get a row
            # for each node in the group.
            #   * the leaf nodes should be the only ones adding rows, so make sure not
            #     to add a row if there's a group at this level
            #   * make sure to add all non-group fields before drilling down into a
            #     group, or all fields won't be picked up
            #   * if there's more than one group, there's no way to drill down into
            #     both simultaneously, so it's not allowed.
            
            next_group_key = None
            for schema_key, field_def in schema["members"].items():
                field_type = field_def[KW_TYPE]
                if field_type in ("group", "datasheet", "schema"):
                    # keep track of this, but process at the end
                    if next_group_key is not None:
                        ValueError("Decode found more than one group at the same level")
                    next_group_key = schema_key
                    continue
                elif field_type in ("collection",):
                    # This is a shallow group, so we can just interate
                    # through it and not have to process it recursively
                    for sub_schema_key, sub_field_def in field_def['members'].items():
                        current_row[sub_schema_key] = record[schema_key][sub_schema_key]
                    continue

                current_row[schema_key] = record[schema_key]

            # If there is a group, process it
            if next_group_key is not None:
                make_rows( 
                        record[next_group_key], 
                        schema['members'][next_group_key], 
                        current_row)        
                return

            rows.append(deepcopy(current_row))

            return


        record = deepcopy(record)
        rows = []
       
        #Style.fg(0x00ffff).print("SCHEMA:", json.dumps(self.schema, indent=4))

        #Style.fg(0xff9900).print("RECORD:", json.dumps(record, indent=4))
 
        current_row = {key: None for key in template}
        #Style.fg(0xff00ff).print("ROW TEMPLATE:", json.dumps(current_row, indent=4))
        
        make_rows(record, self.schema, deepcopy(current_row))
        #Style.fg(0x00ff00).print("ROWS:", json.dumps(rows, indent=4)) 
        
        return rows
        #}}}

    #-----------------------------------------------------------------------------

    @staticmethod
    def create_auto_encoder(part_type_id, part_type_name, record_type, test_name=None):
        #{{{
        record_types = \
        {
            "item": "Item",
            "test": "Test",
            "item image": "Item Image",
            "test image": "Test Image",
        }


        if str(record_type).casefold() not in record_types.keys():
            raise ValueError("'Record Type' should be one of these: "
                            f"{list(record_types.values())}")
        else:
            record_type = record_types[record_type.casefold()]

        try:
            part_type_data = ut.fetch_component_type(part_type_id, part_type_name)
        except ra.MissingArguments:
            raise ValueError("Must identify Part Type in order to create auto-encoder") from None
        part_type_id = part_type_data["ComponentType"]['part_type_id']
        part_type_name = part_type_data["ComponentType"]['full_name']

        if record_type == 'Test':
            if test_name is None:
                raise ValueError("Must identify 'Test Name' when 'Record Type' is 'Test'.")
            elif test_name not in part_type_data["TestTypeDefs"]:
                raise ValueError(f"Part Type does not have a test '{test_name}'")  

        #......................................................................

        def create_item_encoder():
            encoder_def = \
            {
                "Encoder Name": f"_AUTO_{part_type_id}",
                "Record Type": "Item",
                "Part Type ID": part_type_id,
                "Part Type Name": part_type_name,
                "Schema": {"Specifications": {}, "Subcomponents": {}}
            }
            spec = part_type_data["ComponentType"]["properties"]["specifications"][-1]["datasheet"]
            spec = utils.restore_order(deepcopy(spec))
            meta = spec.pop('_meta', {})
            connectors = part_type_data["ComponentType"]["connectors"]

            for k, v in spec.items():
                if k.startswith("_"):
                    continue
                if isinstance(v, list):
                    encoder_def["Schema"]["Specifications"][k] = {
                                "type": "null,any",
                                "choices": v,
                                "default": None,
                                "column": f"S:{k}" 
                            }
                
                else:
                    encoder_def["Schema"]["Specifications"][k] = {
                                "type": "null,json,any",
                                "default": v,
                                "column": f"S:{k}" 
                            }
            for k, v in connectors.items():
                encoder_def["Schema"]["Subcomponents"][k] = {
                            "type": "null,str",
                            "column": f"C:{k}",
                            "default": "<null>" 
                        }

            logger.info(f"default item encoder created:\n{json.dumps(encoder_def, indent=4)}")
            
            return encoder_def

        #......................................................................
        
        def create_test_encoder():
            encoder_def = \
            {
                "Encoder Name": f"_AUTO_{part_type_id}_{test_name.replace(' ', '_')}",
                "Record Type": "Test",
                "Part Type ID": part_type_id,
                "Part Type Name": part_type_name,
                "Test Name": test_name,
                "Schema": {"Test Results": {}}
            }
            test_node = part_type_data["TestTypeDefs"][test_name]["data"]
            spec = test_node["properties"]["specifications"][-1]["datasheet"]
            for k, v in spec.items():
                if k.startswith("_"):
                    continue 

                if isinstance(v, list):
                    encoder_def["Schema"]["Test Results"][k] = {
                            "type": "null,any",
                            "choices": v,
                            "default": None,
                            "column": f"T:{k}"
                        }
                else:
                    encoder_def["Schema"]["Test Results"][k] = {
                            "type": "null,any",
                            "default": v,
                            "column": f"T:{k}"
                        }

            logger.info(f"default test encoder created:\n{json.dumps(encoder_def, indent=4)}")
            
            return encoder_def
        
        #......................................................................

        def create_item_image_encoder():
            
            encoder_def = {
                        "Encoder Name": f"_AUTO_{part_type_id}_Item_Image",
                        "Record Type": "Item Image",
                        "Part Type ID": part_type_id,
                        "Part Type Name": part_type_name,
                        "Schema": {}
                    }

            logger.info(f"default item image encoder created:\n{json.dumps(encoder_def, indent=4)}")
            
            return encoder_def
        
        #......................................................................
        
        def create_test_image_encoder():
           
            if test_name is None:
                raise ValueError("Cannot generate 'Test Image' encoder because "
                            "'Test Name' was not provided.")
 
            encoder_def = {
                        "Encoder Name": f"_AUTO_{part_type_id}_{test_name.replace(' ', '_')}_Image",
                        "Record Type": "Test Image",
                        "Part Type ID": part_type_id,
                        "Part Type Name": part_type_name,
                        "Test Name": test_name,
                        "Schema": {}
                    }

            return encoder_def
        
        #......................................................................

        if record_type == 'Item':
            return create_item_encoder()
        if record_type == 'Test':
            return create_test_encoder()
        if record_type == 'Item Image':
            return create_item_image_encoder()
        if record_type == 'Test Image':
            return create_test_image_encoder()




        #......................................................................

        #}}}

    @staticmethod
    def preserve_schema_order(schema):
        '''Modified version of 'preserve_order' that only preserves it where important

        This is necessary so that two schemas can be compared for differences. You really
        don't want it to flag something as different just because 'type', 'key', and 
        'members' is in a different order!
        '''

        #{{{
        
        def strip_keys(node):
            # if node['_meta']['keys'] exists, get rid of it.
            # if node['_meta'] is now empty, get rid of that, too.
            if '_meta' in node:
                node['_meta'].pop('keys', None)
                if not node['_meta']:
                    # Only pop _meta if there isn't anything else
                    # being stored in there, i.e., it was only there
                    # to hold keys.
                    node.pop('_meta', None)

        def strip_unnecessary_order(node, lvl=0):
            # We're trying to be conscious of the level we're at within the
            # schema, because we don't want to blindly assume at every level
            # that they might have done the same shortcutting ('raw') sort
            # of method that's allowed on the first and second level.

            if lvl == 0:
                # level 0 is schema-level, but we don't know if it's the 
                # shortcut-type or explicit-type yet.
                
                if node.get('type', None) == 'schema':
                    # it's the explicit-type
                    strip_keys(node)
                
                    if 'members' not in node:
                        # there's nothing in this schema, so we can leave.
                        # TODO: consider whether something should happen
                        # if this node contains something besides 'type',
                        # 'members', 'keys', or '_meta'
                        return
                    
                    # advance to the 'members' node and carry on to the 
                    # next level
                    strip_unnecessary_order(node['members'], lvl=1)

                else:
                    # This node shortcutted by listing the members directly,
                    # so advance it to level 1 and try again.
                    strip_unnecessary_order(node, lvl=1)
                return

            if lvl == 1:
                # Level 1 is schema-level, but it's already determined to
                # be shortcut-type.
                # The keys here are the root-level field names.
                # Process each one.
                for k, v in node.items():
                    if k == '_meta':
                        # keep the order, if it's there, but otherwise
                        # skip this node
                        continue

                    if k in ('Specifications', 'Test Results'):
                        # either of these *could* have the fields listed out,
                        # or they could define a 'datasheet' type that has
                        # 'members'
                        if v.get('type', None) == 'datasheet':
                            strip_keys(v)

                            if 'members' not in v:
                                continue

                            strip_unnecessary_order(v['members'], lvl=3)
                            continue

                        else:
                            strip_unnecessary_order(v, lvl=3)
                            continue

                    elif k == 'Subcomponents':
                        # For Subcomponents, do the same, but we don't need 
                        # to recurse. It should just be (key, value) pairs at
                        # whatever node actually contains the members (i.e.,
                        # either the root, or under 'members'
                        if v.get('type', None) == 'collection':
                            strip_keys(v)
                        continue

                    else:
                        # This is some other root level field like 'Comments'
                        # or 'Manufacturer' that doesn't have a hierarchy.
                        # So, the only question is whether the type is just
                        # a string, e.g., "string", "number", etc., or if it's
                        # defined using a dictionary, e.g., {'type':'string',
                        # 'default':'abc'}. If it's the latter, we need to 
                        # strip the order
                        if isinstance(v, dict):
                            strip_keys(v)
                            continue
                return

            if lvl >= 2:
                # Level 2+ is a list of members, where members can possibly 
                # be 'group' type, but they must be explicit. There are no
                # implied shortcut-type groups here.
                for k, v in node.items():
                    if k == '_meta':
                        # keep the order, if it's there, but otherwise
                        # skip this node
                        continue
                
                    if isinstance(v, dict):
                        strip_keys(v)
                        if v.get('type', None) in ('group', 'datasheet', 'collection'):
                            if 'members' not in v:
                                continue
                            else:
                                strip_unnecessary_order(v['members'], lvl+2)
                return

        # Strategy
        # --------
        # Preserve order the normal way, then remove _meta|keys everywhere where
        # they are not needed.

        preserve_order(schema)
        
        strip_unnecessary_order(schema, lvl=0)

        return schema

        #}}}

if __name__ == "__main__":
    pass


