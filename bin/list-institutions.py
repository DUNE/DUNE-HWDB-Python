#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/list-institutions.py
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.RestApiV1 import get_institutions
from Sisyphus.Utils.Terminal import Style
import sys
import json
import argparse

def parse(command_line_args=sys.argv):
    parser = argparse.ArgumentParser(
        add_help=True,
        parents=[config.arg_parser],
        description='Displays a list of available institution codes')
    parser.add_argument('--country',
                        dest='country',
                        metavar='<country code or name>',
                        required=False,
                        help='display only countries matching (or partially matching) string')
    parser.add_argument('--inst-name', '--institution-name',
                        dest='name',
                        metavar='<institution name>',  
                        required=False,
                        help='display only institutions matching (or partially matching) string')
    parser.add_argument('--inst-id',
                        dest='id',
                        metavar='<institution id>',
                        required=False,
                        help='find the specific institution ID')
    args = parser.parse_known_args(command_line_args)
    return args

def main():
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
        country_display_name = f"({country_code}) {country_name}"

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
                inst_id_str = f"({inst_id})".rjust(5)
                if args.name is None:
                    print(f"{inst_id_str} {inst_name}")
                else:
                    print(f"{inst_id_str} {Style.highlight(inst_name, args.name)}")
            print()


if __name__ == '__main__':    
    sys.exit(main())

