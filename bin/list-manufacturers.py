#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/list-institutions.py
Copyright (c) 2023 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

#from Sisyphus.RestApiV1 import get_institutions
from Sisyphus.RestApiV1 import get_manufacturers
from Sisyphus.RestApiV1 import get_component_type
from Sisyphus.RestApiV1 import get_component_types
#from Sisyphus.RestApiV1 import get_projects
from Sisyphus.RestApiV1 import get_systems
from Sisyphus.RestApiV1 import get_subsystems
#from Sisyphus.RestApiV1 import get_components

from Sisyphus.RestApiV1 import Utilities

from Sisyphus.Utils.Terminal import Style
import sys
import json
import argparse

def parse(command_line_args=sys.argv):
    parser = argparse.ArgumentParser(
        add_help=True,
        parents=[config.arg_parser],
        description='Displays a list of available manufacturers')

    group = parser.add_argument_group(
                'Manufacturer List Options',
                'Use the following options to filter the manufacturer list.')

    group.add_argument('--manu-name', '--manufacturer-name',
                        dest='manu_name',
                        metavar='<name>',
                        required=False,
                        help='display only manufacturers matching (or partially matching) string')
    group.add_argument('--manu-id', '--manufacturer-id',
                        dest='manu_id',
                        metavar='<id>',
                        required=False,
                        help='find the specific manufacturer ID')
    group.add_argument('--type-id',
                        dest='type_id',
                        metavar='<part type id>',
                        required=False,
                        help='list only manufacturers defined for this part type ID')
    group.add_argument('--type-name',
                        dest='type_name',
                        metavar='<part type name>',
                        required=False,
                        help='list only manufacturers defined for this part type full name. '
                            '(The full name must be of the form "Z.System.Subsystem.Part".  '
                            '"%%" is allowed as a wildcard within System, Subsystem, or Part, but '
                            'the project code is required.)')

    args = parser.parse_known_args(command_line_args)
    return args

def main():

    args, unknowns = parse()

    manufacturers = get_manufacturer_list(args)

    list_manufacturers(manufacturers)
         
    #find_part_id_by_fullname(fullname)

    #print(Lookup.lookup_part_type_id_by_fullname(fullname))

def get_manufacturer_list(args):


    logger.info("Getting manufacturers")
    
    if args.type_id is not None or args.type_name is not None:
        # Get the type ID, either directly, or via the full name.
        # If they're both given, they MUST match
        if args.type_name is not None:
            try:
                type_name, type_id = Utilities.lookup_part_type_id_by_fullname(args.type_name)
            except ValueError:
                # There is no matching part type ID, so just return an empty list.
                # Ignore the error.
                return {}               
 
            if args.type_id is not None and args.type_id.upper() != type_id:
                return {}
        else:
            type_id = args.type_id.upper()

        # Now get the component type for that type id
        resp = get_component_type(type_id)

        if resp['status'] != "OK":
            msg = "There was an error getting the part type ID from the server"
            logger.error(msg)
            raise RuntimeError(msg)

        manufacturers = resp['data']['manufacturers']

    else:
        # Get the full list of manufacturers instead
        resp = get_manufacturers()
        
        if resp['status'] != "OK":
            msg = "There was an error obtaining a list of manufacturers from the server"
            print(msg)
            logger.error(msg)
            return 1

        manufacturers = resp['data']

    # Now let's thin it out by manufacturer ID or name, if given
    m2 = [
        (item['id'], item['name']) for item in manufacturers
            if (args.manu_id is None or str(item['id'])==str(args.manu_id))
            and (args.manu_name is None or args.manu_name.upper() in item['name'].upper()) ]
    manufacturers = {k:v for (k, v) in sorted(m2)}
    
    return manufacturers

def list_manufacturers(manufacturers):

    logger.info("Listing manufacturers")
    
    if len(manufacturers) == 0:
        msg = "No manufacturers found matching criteria"
        print()
        print(msg)
        print()
        logger.warning(msg)
        return 0

    print()    
    print("Manufacturers found:")
    print()
    #print(manu_ids)

    print(" (ID) Name")
    print("===== ==================================================")
    
    for manu_id, manu_name in manufacturers.items():
        manu_id_str = f"({manu_id})".rjust(5)
        print(f"{manu_id_str} {manu_name}")

    print()


    #print(json.dumps(resp, indent=4))

    """
    logger.info("Listing institutions")

    args, unknowns = parse()

    resp = get_institutions()

    if resp['status'] != "OK":
        print("There was an error obtaining a list of institutions from the server")
        return 1

    # Separate by country
    inst_by_country = {}
    countries = []
    for inst in resp['data']:
        country_code = inst['country']['code']
        country_name = inst['country']['name']
        inst_id = inst['id']
        inst_name = inst['name']

        country_display_name = f"{country_name} ({country_code})"

        if args.country is not None:
            if args.country.upper() not in country_display_name.upper():
                # skip this institution
                continue
        if args.name is not None:
            if args.name.upper() not in inst_name.upper():
                # skip this institution
                continue
        if args.id is not None:
            if args.id != str(inst_id):
                # skip this institution
                continue

        if country_code not in inst_by_country.keys():
            inst_by_country[country_code] = []
            countries.append((country_code, country_display_name))
        inst_by_country[country_code].append((inst_id, inst_name))

    countries = [ (a, b) for (b, a) in 
                sorted([(b, a) for (a, b) in countries]) ]
   
    if len(countries) == 0:
        print()
        print("No institutions found matching criteria")
        print()
    else:
        print()
        print("Institutions found:")
        print()
        for country_code, country_display_name in countries:

            institutions = [ (a, b) for (b, a) in 
                    sorted([(b, a) for (a, b) in inst_by_country[country_code]]) ]
        
            if args.country is None:
                print(country_display_name)
            else:
                print(Style.highlight(country_display_name, args.country))

            print("="*len(country_display_name))
            for inst_id, inst_name in institutions:
                if args.name is None:
                    print(f"{inst_id:3d} {inst_name}")
                else:
                    print(f"{inst_id:3d} {Style.highlight(inst_name, args.name)}")
            print()
    """

if __name__ == '__main__':    
    sys.exit(main())

