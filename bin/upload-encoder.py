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
                'help': "Docket file containing Encoders to be uploaded"}
        ),
        (
            ('--include-all', '-a'),
            {'action': 'store_true',
                'help': "Upload all Encoders found in specified file. "
                        "(additional 'include' flags are ignored.)"}  
        ),
        (
            ('--include-name',),
            {'metavar': "<encoder-name>", 'nargs': 1, 'action': 'append',
                'help': 'include encoder named <encoder name>'
            }
        ),
        #(
        #    ('--include-encoders',),
        #    {'metavar': "<part-type>", 'nargs': 1, 'action': 'append',
        #        'help': 'include all item and test encoders for given part type'
        #    }
        #),
        #(
        #    ('--include-item-encoder',),
        #    {'metavar': "<part-type>", 'nargs': 1, 'action': 'append',
        #        'help': 'include only the item encoder for given part type'
        #    }
        #),
        #(
        #    ('--include-test-encoders',),
        #    {'metavar': "<part-type>", 'nargs': 1, 'action': 'append',
        #        'help': 'include only the test encoders for given part type'
        #    }
        #),
        #(
        #    ('--include-test-encoder',),
        #    {'metavar': ("<part-type>", "<test-name>"), 'nargs': 2, 'action': 'append',
        #        'help': 'include test encoder for given part type and test name'
        #    }
        #),
        (
            ('--submit', '-x'),
            {'dest': 'submit', 'action': 'store_true'}
        ),
    ]


    for args, kwargs in arg_table:
        group.add_argument(*args, **kwargs)


    args = parser.parse_known_args(command_line_args)
    return args
    #}}}

def find_encoders(args):

    dockets = []

    encoders_by_name = {}
    encoders_by_part_type = {}

    if len(args.files) == 1:
        Style.error.print("Error: No docket files were given.")
        print()
        return []

    for filename in args.files[1:]:
        dockets.append(Docket(filename=filename, encoders_only=True))

    for docket in dockets:
        for key, encoder_def in docket.encoders.items():
            enc = Encoder(encoder_def)
            
            # append the encoder to encoders_by_name, if it has a name.
            # multiple encoders with the same name is okay as long as
            # that isn't the encoder asked for.
            if enc.name is not None:
                logger.debug(f"adding name '{enc.name}' from docket '{docket.docket_name}'")
                encoders_by_name.setdefault(enc.name, []).append(enc)

            # append to encoders_by_part_type. Again, multiples are okay
            # as long as it's not the one asked for.
            encoders_by_part_type.setdefault(enc.part_type_id, {})
            pt_node = encoders_by_part_type[enc.part_type_id]

            if enc.record_type == "Item":
                pt_node.setdefault("Item", []).append(enc)
            elif enc.record_type == "Test":
                pt_node.setdefault("Test", {}).setdefault(enc.test_name, []).append(enc)
            
    def append_to_targets(targets, enc):
        # Look through targets to make sure this encoder isn't already there,
        # and append this encoder to the list if it's not.
        # It's possible for someone to include an encoder both by name and 
        # by part type, in which case, it would be found more than once, but
        # we can check its 'id' property to see if it's the same exact object.
        # If it is, that's okay. Don't add it again, but it's not an error.
        targets.setdefault(enc.part_type_id, {})
        if enc.record_type == "Item":
            existing_enc = targets[enc.part_type_id].setdefault("Item", None)
            if not existing_enc:
                # Good, no problem here
                targets[enc.part_type_id]["Item"] = enc
                return True
            elif id(enc) == id(existing_enc):
                # We ended up finding the exact same encoder.
                # Don't add it again, but it's not an error.
                return True
            else:
                # Somehow, we ended up loading two distinct item encoders
                # for the same part type. This is an error.
                return False
        else:
            existing_enc = (targets[enc.part_type_id].setdefault("Test", {})
                                .setdefault(enc.test_name, None))
            if not existing_enc:
                targets[enc.part_type_id]["Test"][enc.test_name] = enc
                return True
            elif id(enc) == id(existin_enc):
                return True
            else:
                return False

    targets = {}

    if args.include_all:
        # Go through all encoders_by_part_type (and ignore encoders_by_name)
        # and add them to targets. Duplicates are an error.

        for ptid, container in encoders_by_part_type.items():
            if len(container['Item']) > 1:
                Style.error.print(f"Error: More than one Item Encoder found for {ptid}")
                print()
                return None
            append_to_targets(targets, container['Item'][0])

            for test_name, test_list in container.get("Test", {}).items():

                if len(test_list) > 1:
                    Style.error.print(f"Error: More than one Test Encoder found for {ptid} "
                            f"'{test_name}'")
                    print()
                    return None
                append_to_targets(targets, test_list[0])

        # For include_all, we ignore the rest of the parameters, so exit
        return targets

    if args.include_name:
        # Look for encoders in the docket that have Encoder Name matching names 
        # supplied in the args.

        names = [ p[0] for p in args.include_name ]

        for name in names:

            enc_list = encoders_by_name.get(name, [])
            if not enc_list:
                Style.warning.print(f"Warning: No encoders found named '{name}'")
            elif len(enc_list) > 1:
                Style.error.print(f"Error: Multiple encoders found named '{name}'")
                print()
                return None
            
            enc = enc_list[0]

            if not append_to_targets(targets2, enc):
                if enc.record_type == 'Item':
                    Style.error.print(f"Error: More than one encoder for "
                                f"part_type_id='{enc.part_type_id}'")
                else:
                    Style.error.print(f"Error: More than one encoder for "
                                f"part_type_id='{enc.part_type_id}' "
                                f"test_name='{enc.test_name}'")
                return None

    return targets

    '''
    # It gets more complicated from here, because now we we have to collect
    # from several different types of includes, and then normalize the
    # part type and test name with what exists in the database.
    
    # Gather all the 'includes' and put them here. Don't do lookups yet.
    include_manifest = []

    if args.include_encoders:
        # For each part type in this list, add the item encoder and all test
        # encoders
        for part_type in [ p[0] for p in args.include_encoders ]:
            include_manifest.append({
                "part_type": part_type,
                "include_item": True,
                "include_tests": True
            })
            
    if args.include_item_encoder:
        # For each part type in this list, add the item encoder but no tests
        for part_type in [ p[0] for p in args.include_item_encoder ]:
            include_manifest.append({
                "part_type": part_type,
                "include_item": True,
                "include_tests": False
            })

    if args.include_test_encoders:
        # For each part type in this list, add the test encoders but not the item
        for part_type in [ p[0] for p in args.include_test_encoders ]:
            include_manifest.append({
                "part_type": part_type,
                "include_item": False,
                "include_tests": True
            })
    
    if args.include_test_encoder:
        # For each part type in this list, add only the test indicated
        for part_type, test_name in [ p[0] for p in args.include_test_encoder ]:
            include_manifest.append({
                "part_type": part_type,
                "include_item": False,
                "include_tests": test_name
            })
        
    for include in include_manifest:
        if include["part_type"].find('.') != -1:
            # This part type is a name. Let's look it up.
            part_types = ut.lookup_part_type_by_name(part_type_name=include["part_type"])
        else:
            resp = ut.fetch_component_type(part_type_id=include["part_type"])
            part_types = [ut.PartType(resp["ComponentType"]["part_type_id"], 
                            resp["ComponentType"]["full_name"])]
        print(f"part_types: {part_types}")

    if args.include_encoders:
        # Look for encoders matching the part type id or part type name in the
        # command line args

        print(f"include encoders: {args.include_encoders}")

        raw_part_type_list = [ p[0] for p in args.include_encoders ]

        # We need to resolve the part types in this list.
        # Note that it's okay if there are duplicates in what is requested.
        # It's only an error if we find duplicate matches in what's in the
        # docket.
        part_type_list = {}
        for part_type_id_or_name in raw_part_type_list:
            print(f"part type: {part_type_id_or_name}")

            # We'll say that if it contains '.' then it's a name, otherwise,
            # it's an id
            if part_type_id_or_name.find('.') != -1: # Assume it's a name
                part_type_id = None
                part_type_name = part_type_id_or_name
            else: # Assume it's a part type id
                part_type_id = part_type_id_or_name
                part_type_name = None
            try:
                resp = ut.fetch_component_type(
                            part_type_id=part_type_id, part_type_name=part_type_name)
            except ra.NotFound as ex:
                Style.error.print(f"Error: part type '{part_type_id_or_name}' "
                        "had no matches in the HWDB.")
                print()
                return []

            part_type_id = resp["ComponentType"]["part_type_id"]
            part_type_name = resp["ComponentType"]["full_name"]
            part_type_list[part_type_id] = part_type_name


        print(part_type_list)

    return targets
    '''

def upload_encoders(targets, submit=False):
    #print("targets:")
    #print(targets)

    for part_type_id, node in targets.items():
        item_enc = node.get("Item", None)
        if item_enc is not None:
            success = item_enc.store(dryrun=not submit)
            Style.info.print(f"{item_enc.part_type_id}: {'Uploaded' if success else 'Not Updated'}")

        test_node = node.get("Test", {})

        for test_name, test_enc in test_node.items():
            success = test_enc.store(dryrun=not submit)
            Style.info.print(f"{test_enc.part_type_id} {test_enc.test_name}: "
                        f"{'Uploaded' if success else 'Not Updated'}")









def main():
    logger.info(f"Starting {__name__}")
    Sisyphus.display_header() 

    args, unknowns = parse()

    targets = find_encoders(args) 

    if targets:
        upload_encoders(targets, args.submit)
    else:
        Style.error.print("Error: No targets found to upload")
        print()


    logger.info(f"Finished {__name__} and exiting.")

if __name__ == '__main__':    
    sys.exit(main())

