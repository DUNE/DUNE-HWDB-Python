#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/configure.py
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

import sys
import argparse
import Sisyphus
import Sisyphus.Configuration as Config
from Sisyphus.Configuration import config
logger = config.getLogger(__name__)
from Sisyphus.Utils.Terminal import Image
from Sisyphus.Utils.Terminal.Style import Style

def parse(command_line_args=sys.argv):
    logger.debug("parsing args")
    parser = argparse.ArgumentParser(
        add_help=True,
        parents=[Config.config.arg_parser],
        description='Saves authentication info in ~/.sisyphus/config.json')

    group = parser.add_argument_group(
                'Configuration Utility Options',
                'All configuration options above will be permanent, and the '
                'following additional options are available.')
        
    group.add_argument('--reset',
                        dest='reset',
                        action='store_true',
                        required=False,
                        help='resets everything in the configuration '
                             '(i.e., reset the configuration, then add everything '
                             'else provided in this command line')
    args = parser.parse_known_args(command_line_args)
    return args

def check_server(profile):
    # we wait until here to import because we want to process arguments and 
    # update the configuration before accessing the HWDB.
    import Sisyphus.RestApiV1 as ra
    try:
        resp = ra.whoami(profile=profile)
    except ra.CertificateError as err:
        msg = "The server does not recognize the certificate"
        config.logger.error(msg)
        config.logger.info(f"The exception was: {err}")
    except Exception as err:
        msg = "Failed to contact server to validate certificate"
        config.logger.error(msg)
        config.logger.info(f"The exception was: {err}")
    else:
        import json
        data = resp['data']
        user = f"{data['full_name']} ({data['username']})"
        user_id = data['user_id']
        msg = f"REST API 'whoami' returned {user}, user_id: {user_id}"
        config.logger.info(msg)

    return msg


def show_summary(config):
    print("Configuration Summary:")
    print("======================")
    
    print(f"profile:      {config.active_profile.profile_name}")

    if config.active_profile.rest_api == Config.RESTAPI_DEV:
        rest_api_msg = "(development)"
    elif config.active_profile.rest_api == Config.RESTAPI_PROD:
        rest_api_msg = "(PRODUCTION)"
    else:
        rest_api_msg = "(custom)"

    print(f"REST API:     {config.active_profile.rest_api} {rest_api_msg}")
   
    sys.stdout.write("server check: (please wait)")
    sys.stdout.flush()
    check_result = check_server(config.active_profile)
    sys.stdout.write(f"\rserver check: {check_result}\033[K\n")

    print()

def log_test():
    logger.debug("test debug message")
    logger.info("test info message")
    logger.warning("test warning message")
    logger.error("test error message")
    logger.critical("test critical message")
 
def main():
    logger.info(f"Starting {__name__}")
    Sisyphus.display_header() 

    args, unknowns = parse()
    
    if args.reset:
        Config.config.reset()
    #if args.set_active:
    #    Config.config.set_active()
    
    Config.config.save()
    show_summary(Config.config)
    logger.info(f"Finished {__name__} and exiting.")

    log_test()

    logger.info(f"Finished {__name__} and exiting.")

if __name__ == '__main__':    
    sys.exit(main())

