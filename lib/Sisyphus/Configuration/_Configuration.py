#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/Configuration/_Configuration.py
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

# This module should NOT import anything else from this project that uses
# Config or uses anything that uses Config

import Sisyphus # for version and some file paths
from Sisyphus.Utils.Terminal.Style import Style

import os
import shutil
import json, json5
import sys
import argparse
import subprocess
import tempfile
import re
import OpenSSL
import requests
from datetime import datetime

import logging
import logging.config


API_DEV = 'dbwebapi2.fnal.gov:8443/cdbdev'
API_PROD = 'dbwebapi2.fnal.gov:8443/cdb'
DEFAULT_API = API_DEV

MY_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__)))
USER_SETTINGS_DIR = os.path.normpath(os.path.expanduser("~/.sisyphus"))

USER_CONFIG_FILE = os.path.join(USER_SETTINGS_DIR, "config.json")
DEFAULT_LOG_CONFIG_FILE = os.path.join(MY_PATH, "default_log_config.py")
LOG_CONFIG_FILE = os.path.join(USER_SETTINGS_DIR, "log_config.py")

KW_DEFAULT_PROFILE = "default profile"
KW_PROFILES = "profiles"
KW_REST_API = "rest api"
KW_CERT_TYPE = "certificate type"
KW_CERTIFICATE = "certificate"
KW_P12 = "p12"
KW_PEM = "pem"
KW_LOGGING = "logging"
KW_LOGLEVEL = "loglevel"
KW_SETTINGS = "settings"

class Config:
    def __init__(self, *, 
            user_settings_dir=None, user_config_file=None, log_config_file=None, args=sys.argv):
        #{{{
        self.original_args = args

        self.user_config_file = (user_config_file or USER_CONFIG_FILE)
        self.log_config_file = (log_config_file or LOG_CONFIG_FILE)
        self.user_settings_dir = (user_settings_dir or USER_SETTINGS_DIR)

        self.logger = self.getLogger("Config")
        self.logger.info("[LOG INIT] logging initialized")
        self.logger.info(f"[LOG INIT] ver={Sisyphus.version}")
        self.logger.info(f"[LOG INIT] path={Sisyphus.project_root}")
 
        self._parse_args(args)
        self.load()
        #}}}

    def getLogger(self, name="unnamed"):
        #{{{     
        if not getattr(self, "_logging_initialized", False):
            self._init_logging()
        
        already_loaded = (name in logging.Logger.manager.loggerDict
                and not isinstance(logging.Logger.manager.loggerDict[name], logging.PlaceHolder))

        logger = logging.getLogger(name)
       
        if getattr(self, "active_profile", None) is not None:
            if self.active_profile[KW_LOGLEVEL] is not None:
                logger.setLevel(self.active_profile[KW_LOGLEVEL])
        if not already_loaded:
            logger.debug(f"created logger '{name}'")
        #else:
        #    logger.debug(f"returning logger '{name}'")
        return logger
        #}}}

    def load_additional_config(self, filename, recopy_on_error=False):
        filepath = os.path.join(USER_SETTINGS_DIR, filename)

        def load_config():
            with open(filepath, 'r') as fp:
                raw_data = fp.read()

                _locals, _globals = {}, {}
                exec(raw_data, _globals, _locals)
            
            return _locals["contents"]

        def reset_config():
            try:
                src_file = os.path.join(MY_PATH, filename)
                with open(src_file, "r") as f:
                    raw_data = f.read()
            except Exception:
                msg = f"The configuration file at '{src_file}' could not be read."
                raise RuntimeError(msg)

            raw_data = raw_data.replace("${SISYPHUS_VERSION}", Sisyphus.version)

            try:
                with open(filepath, "w") as fp:
                    fp.write(raw_data)
                os.chmod(filepath, mode=0o600)
            except Exception:
                msg = f"The config file '{filepath}' could not be created."
                raise RuntimeError(msg)

        try:
            config = load_config()
        except:
            if recopy_on_error:
                reset_config()
                config = load_config()
            else:
                raise

        return config
            
            
            
    

    def _init_logging(self):
        #{{{ 
        # We need to create the directory the logs will be written to
        try:
            path = os.path.dirname(self.log_config_file)
            os.makedirs(path, mode=0o700, exist_ok=True) 
        except Exception:
            msg = f"Could not create the log directory at {path}"
            raise RuntimeError(msg)
   
        # Read and use the data in log_config_file, if it exists
        # If it doesn't exist, or if it is corrupt, create a new one

        def configure_logs():
            # Try to read the configuration file and let any exceptions
            # bubble up to the next level.
                    
            with open(self.log_config_file, "r") as f:
                raw_data = f.read()
            
            _locals = {}
            _globals = {} #globals()
            exec(raw_data, _globals, _locals)
            
            # we will use "all" here because we don't want the usual
            # short-circuit logic to apply. We want to make sure _locals
            # has both of these variables.
            if all([_locals["overwrite_on_new_version"], 
                    _locals["sisyphus_version"] != Sisyphus.version]):
                raise ValueError("log config is obsolete")

            self.log_config_dict = _locals["contents"]

            # Unfortunately, Python's logging module doesn't do an 
            # expanduser on the logging handlers, so we have to go into
            # that part of the configuration and do it ourselves.
            for handler_name, handler_def in self.log_config_dict["handlers"].items():
                if "filename" in handler_def:
                    handler_def["filename"] = os.path.expanduser(handler_def["filename"])

            logging.config.dictConfig(self.log_config_dict)

        try:
            configure_logs()
        except Exception:
            self.reset_log_config()
            configure_logs()

        self._logging_initialized = True   
        #}}}
        
    @property 
    def log_settings(self):
        return self.log_config_dict #[KW_LOGGING]
    
    @property
    def rest_api(self):
        return self.active_profile[KW_REST_API]
    
    @property
    def certificate(self):
        return self.active_profile[KW_CERTIFICATE]

    @property
    def cert_type(self):
        return self.active_profile[KW_CERT_TYPE]

    @property
    def default_profile(self):
        return self.config_data[KW_DEFAULT_PROFILE]

    @property
    def settings(self):
        return self.config_data.get(KW_SETTINGS, {})

    def _extract_cert_info(self):
        #{{{
        self.logger.debug("Extracting certificate information")
            
        self.cert_has_expired = None
        self.cert_expires = None
        self.cert_fullname = None
        self.cert_username = None
        self.cert_days_left = None
        
        if self.active_profile[KW_CERTIFICATE] is None:
            self.logger.debug("There is no certificate to extract data from.")
            return 
        if self.cert_type == KW_P12:       
            self.logger.debug("Unable to extract data from P12 certificate without password")
            return 

 
        with open(self.active_profile[KW_CERTIFICATE], "r") as fp:
            ce = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, fp.read())
        
        self.cert_has_expired = ce.has_expired()
        self.cert_expires = datetime.strptime(
                    ce.get_notAfter().decode('utf-8'), '%Y%m%d%H%M%S%z').astimezone()
        
        if self.cert_has_expired:
            self.cert_days_left = 0
        else:
            current = datetime.now().astimezone()
            self.cert_days_left = (self.cert_expires - current).days
        
        comps = [(k.decode('utf-8'), v.decode('utf-8')) for k, v in ce.get_subject().get_components()]
        
        try:
            self.cert_fullname = [ v for k, v in comps if k=='CN' and not v.startswith('UID:')][0]
        except Exception:
            self.cert_fullname = None
        
        try:
            self.cert_username = [ v for k, v in comps if k=='CN' and v.startswith('UID:')][0][4:]
        except Exception:
            self.cert_username = None
    
    
        log_msg = (f"Certificate info: {self.cert_fullname} ({self.cert_username}), "
                   f"expires {self.cert_expires.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.debug(log_msg)
        #}}}             
    
    def reset(self):
        self.reset_log_config()
        self.config_data = {}
        
    def set_active(self):
        self.config_data[KW_DEFAULT_PROFILE] = self.profile_name
    
    def remove(self, profile_name=None):
        #{{{
        if profile_name is None:
            profile_name = self.profile_name
            
        if profile_name in self.profiles.keys():
            self.profiles.pop(profile_name)
            self.logger.info(f"Removed profile '{profile_name}' from configuration")
        else:
            self.logger.info(f"Unable to remove profile '{profile_name}' from configuration "
                             "because it does not exist.")
        #}}}
                
    def save(self):
        #{{{
        '''Make the current config permanent'''

        # create the config directory, if needed
        if not os.path.exists(self.user_config_file):
            try:
                path = os.path.dirname(self.user_config_file)
                os.makedirs(path, mode=0o700, exist_ok=True) 
            except Exception:
                msg = "The configuration directory does not exist and could not be created."
                raise RuntimeError(msg)

        # If we started from a p12 file and extracted a certificate, save the certificate
        if hasattr(self, 'temp_pem_file'):
            perm_filename = os.path.join(self.user_settings_dir, f"certificate_{self.profile_name}.pem")
            shutil.copyfile(self.temp_pem_file.name, perm_filename)
            self.active_profile[KW_CERTIFICATE] = perm_filename
            del self.temp_pem_file
        
        # Delete any saved certificates that don't correspond to a current profile
        pattern = re.compile('certificate_(.*)\\.pem')
        files = {
                pattern.match(f).group(1): f 
                    for f in os.listdir(self.user_settings_dir) 
                    if pattern.match(f) is not None
        }
        profiles = list(self.config_data["profiles"].keys())
        for k, v in files.items():
            if k not in profiles:
                filepath = os.path.join(self.user_settings_dir, v)
                os.remove(filepath)
        
        # Save the config file
        try:
            with open(self.user_config_file, "w") as f:
                f.write(json.dumps(self.config_data, indent=4))
            os.chmod(self.user_config_file, mode=0o600)
        except Exception:
            msg = "The configuration file could not be created."
            raise RuntimeError(msg)
        #}}}
                
    def load(self):
        #{{{
        self.logger.debug("Loading config file and merging with command line args")
        self._load_config(self.user_config_file)
        self._populate_config()
        self._extract_cert_info()
        #}}}

    def _extract_pem(self, p12_file, password):
        #{{{
        #print(p12_file)

        import ssl
        use_legacy = ssl.OPENSSL_VERSION.startswith("OpenSSL 3")
       
        self.temp_pem_file = tempfile.NamedTemporaryFile(
            mode='w+b', 
            buffering=- 1, 
            encoding=None, 
            newline=None, 
            suffix=".pem", 
            prefix="tmp_", 
            dir=self.user_settings_dir, 
            delete=True,
            errors=None)
        
        #print(dir(self.temp_pem_file))
        #print(self.temp_pem_file)
    
        tokens =  [
                    "openssl",
                    "pkcs12",
                    "-in", p12_file,
                    #"-out", outfile,
                    "-nodes",
                    "-passin", f"pass:{password}",
                ]
    
        if use_legacy:
            tokens.append("-legacy")

        gen_pem = subprocess.Popen(
                            tokens,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
        
        output, errors = gen_pem.communicate()
                
        if gen_pem.returncode != 0:
            raise RuntimeError(f"Unable to extract pem certificate from p12 file: "
                            f"{errors.decode('utf-8').strip()}")
        else:
            self.temp_pem_file.write(output)
            self.temp_pem_file.flush()
        #}}}

    def _populate_config(self):
        #{{{
        # populate the Config object using data from both the configuration file
        # and the command line arguments. Command line arguments have priority.
        #
        # Note that this doesn't actually save the configuration for future runs!
        # You must call Config.save() to make this permanent.
        
        # identify which profile we're working with
        if self.args.profile is not None:
            self.profile_name = self.args.profile
            self.logger.debug(f"profile set to '{self.profile_name}'")
            
            # if there's no default profile, make this the default.
            if self.config_data.get(KW_DEFAULT_PROFILE, None) is None:
                self.config_data[KW_DEFAULT_PROFILE] = self.profile_name
                self.logger.debug(f"default profile set to '{self.config_data[KW_DEFAULT_PROFILE]}'")
        else:
            self.profile_name = self.config_data[KW_DEFAULT_PROFILE] = \
                        self.config_data.get(KW_DEFAULT_PROFILE, "default")
            self.logger.debug(f"using profile '{self.profile_name}'")
            
        # get the profile data for the active profile            
        profiles = self.config_data[KW_PROFILES] \
                    = self.config_data.get(KW_PROFILES, {self.profile_name: {}})
        active_profile = self.active_profile \
                    = profiles[self.profile_name] \
                    = profiles.get(self.profile_name, {})
        
        # set the log level (which will be effective only AFTER config initializes, so there
        # will be some initial info or debug messages even if level is set higher)
        log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'default']
        if self.args.loglevel is not None:
            if self.args.loglevel not in log_levels:
                err_msg = f"Error: --loglevel must be in {log_levels}"
                self.logger.error(err_msg)
                raise ValueError(err_msg)
            else:
                if self.args.loglevel != 'default':
                    active_profile[KW_LOGLEVEL] = self.args.loglevel
                else:
                    active_profile[KW_LOGLEVEL] = None
        else:
            active_profile[KW_LOGLEVEL] = active_profile.get(KW_LOGLEVEL, None)

        # get the REST API
        if [self.args.rest_api is not None, self.args.dev, self.args.prod].count(True) > 1:
            err_msg = "Error: --rest-api, --dev, and --prod are mutually exclusive" 
            self.logger.error(err_msg)
            raise ValueError(err_msg)

        if self.args.rest_api is not None:
            active_profile[KW_REST_API] = self.args.rest_api
        elif self.args.dev:
            active_profile[KW_REST_API] = API_DEV
        elif self.args.prod:
            active_profile[KW_REST_API] = API_PROD
        else:
            active_profile[KW_REST_API] = active_profile.get(KW_REST_API, DEFAULT_API)

        self.logger.info(f"using rest api '{active_profile[KW_REST_API]}'")
        
        # let's figure out the certificate situation...
        # 0) if --cert is provided without --cert-type, it will guess based on the
        #    extension.
        # 1) if the command line args are --cert-type p12 --cert 'xxx.p12' --password 'xxx',
        #    extract a pem from it and make it a temporary file. The config type
        #    will be "pem" instead of "p12". The temp file will only be made 
        #    permanent if the config is saved, and future runs using this config
        #    will not need a password.
        # 2) if the args are the same but with no password,
        #    use this file at its given location. The config type will be "p12".
        #    If saved, copy the file to the config directory. Future runs will require
        #    a password.  (The current run won't be able to use the REST API.)
        # 3) If the args are --cert-type pem --cert 'xxx.pem',
        #    use this file at its given location. If the config is saved, copy it to
        #    the config directory and use that from then on.
        # 4) If there is only --password 'xxx',
        #    then the config file must contain a p12. Continue as per case #1. If saved,
        #    the cert type will be pem instead of p12.
        # 5) If there are no args, use whatever was in the config file.
        #
        # * It is an error to supply a non-existent file or an incorrect password
        # * It is an error to give a password if the cert type is pem.
        # * It is an error to give a cert type without a cert (even if there's a cert in 
        # *   the config file)
        # * It is NOT an error to supply insufficient information, but you won't be able
        #     to use the REST API.
        
        # If these are provided in command line arguments, we need to do some processing
        # before throwing them into the config structure.
        if self.args.cert is not None:
            if self.args.cert_type is not None:
                if self.args.cert_type.lower() in (KW_P12, "pem"):
                    args_cert_type = self.args.cert_type.lower()
                else:
                    raise RuntimeError("Error: certificate type must be 'pem' or 'p12'")
            elif self.args.cert.lower().endswith(KW_P12):
                args_cert_type = KW_P12
            elif self.args.cert.lower().endswith(KW_PEM):
                args_cert_type = KW_PEM
            else:
                raise RuntimeError("Error: certificate type must be 'pem' or 'p12'")
            
            active_profile[KW_CERTIFICATE] = self.args.cert
            active_profile[KW_CERT_TYPE] = args_cert_type
        else:
            if self.args.cert_type is not None:
                raise RuntimeError("Error: certificate type provided, but no certificate")
            active_profile[KW_CERTIFICATE] = active_profile.get(KW_CERTIFICATE, None)
            active_profile[KW_CERT_TYPE] = active_profile.get(KW_CERT_TYPE, None)
            
        if active_profile[KW_CERT_TYPE] == KW_PEM and self.args.password is not None:
            raise RuntimeError("Error: passwords cannot be used with pem certificates")
        
        active_profile[KW_CERTIFICATE] = active_profile.get(KW_CERTIFICATE, self.args.cert)
        
        # Now the hard part. If it's a p12 with a password, we should convert to pem.
        if active_profile[KW_CERT_TYPE] == KW_P12:
            if self.args.password is not None:
                self.logger.debug("extracting PEM certificate from P12")
                self._extract_pem(active_profile[KW_CERTIFICATE], self.args.password)
                active_profile[KW_CERT_TYPE] = KW_PEM
                active_profile[KW_CERTIFICATE] = self.temp_pem_file.name
            else:
                self.logger.debug("Using P12 certificate, but no password was supplied")
        else:
            #self.logger.debug(f"{active_profile[KW_CERT_TYPE]}, {self.args.password}")
            self.logger.debug("using PEM certificate")
        #}}}
    
    def _load_config(self, filename):
        #{{{
        # open the file
        try:
            with open(filename, "r") as f:
                raw_data = f.read()
        except Exception:
            # msg = f"The configuration file at '{filename}' could not be read."
            # raise RuntimeError(msg)
            self.config_data = {}
            return
        
        # parse it as JSON5
        try:
            self.config_data = json5.loads(raw_data)
        except Exception as ex:
            raise RuntimeError(f"'{filename}' was not a valid JSON/JSON5 file --> {ex}")

        # Let's check for a new version, but don't do it more than once per day
        today = datetime.now().date().strftime("%Y-%m-%d")
        if self.config_data.get("version", None) is not None:
            if self.config_data["version"].get("last checked", None) >= today:
                self.latest_release_version = self.config_data["version"]["latest release version"]
        if getattr(self, "latest_release_version", None) is None:
            self.config_data["version"] = \
            {
                "current version": Sisyphus.version,
                "latest release version": self.get_latest_release_version(),
                "last checked": today,
            }                
            with open(filename, "w") as f:
                f.write(json.dumps(self.config_data, indent=4))


        #}}}

    def _parse_args(self, args=None):
        #{{{
        self.arg_parser = argparse.ArgumentParser(allow_abbrev=False, add_help=False)        

        group = self.arg_parser.add_argument_group(
                        Style.notice('Global Configuration Options'),
                        'These options are available for most scripts, and are only set '
                        'for the duration of the script. If used with the '
                        'Configuration Utility, however, they will be set permanently.')

        group.add_argument('--cert-type',
                            dest='cert_type',
                            metavar='[ p12 | pem ]',
                            required=False,
                            #help='type of certificate file being used: p12 or pem')
                            help=argparse.SUPPRESS)
        group.add_argument('--cert',
                            dest='cert',
                            metavar='<filename>',
                            required=False,
                            help='user certificate for accessing REST API')
        group.add_argument('--password', 
                            dest='password',
                            metavar='<password>',
                            required=False,
                            help='password, required if using a p12 file. '
                                 '(The utility will extract a pem certificate '
                                 'and use that; the password will not be retained.')
        group.add_argument('--dev',
                            dest='dev',
                            action='store_true',
                            required=False,
                            help=f'use the DEVELOPMENT server at {API_DEV}')
        group.add_argument('--prod',
                            dest='prod',
                            action='store_true',
                            required=False,
                            help=f'use the PRODUCTION server at {API_PROD}')
        group.add_argument('--rest-api',
                            dest='rest_api',
                            metavar='<url>',
                            required=False,
                            help=f'use the REST API at <url>, ex. {DEFAULT_API}')
        group.add_argument('--profile',
                            dest='profile',
                            metavar='<profile-name>',
                            required=False,
                            help="if multiple profiles exist in the system, use the profile "
                                "named <profile-name>. Otherwise, use the default profile.")
        group.add_argument('--loglevel',
                            dest='loglevel',
                            metavar='<loglevel>',
                            required=False,
                            help="Only log messages at <loglevel> or higher in severity. "
                                "(DEBUG, INFO, WARNING, ERROR, CRITICAL, or 'default' to "
                                "use the default level")    

        group.add_argument('--version',
                            action='version',
                            version=f'Sisyphus {Sisyphus.version}')

        self.args, self.remaining_args = self.arg_parser.parse_known_args(args)
        #}}}    

    def reset_log_config(self):
        #{{{
        '''Generate the settings for the Logging module'''
        
        try:
            with open(DEFAULT_LOG_CONFIG_FILE, "r") as f:
                raw_data = f.read()
        except Exception:
            msg = f"The log configuration file at '{self.log_config_file}' could not be read."
            raise RuntimeError(msg)

        raw_data = raw_data.replace("${SISYPHUS_VERSION}", Sisyphus.version)

        try:
            with open(self.log_config_file, "w") as f:
                f.write(raw_data)
            os.chmod(self.log_config_file, mode=0o600)
        except Exception:
            msg = "The logging config file could not be created."
            raise RuntimeError(msg)
        #}}}

    def get_latest_release_version(self):
        if getattr(self, "tag_name", None) is None:
            resp = requests.get("https://api.github.com/repos/DUNE/DUNE-HWDB-Python/releases/latest")   
            self.latest_release_version = resp.json()["tag_name"]
        return self.latest_release_version

    def newer_version_exists(self):
        re_version = re.compile(r"""
                ^[v]{0,1}(?P<version>.*)$
            """, re.VERBOSE)
        current_version = tuple(re_version.match(Sisyphus.version)["version"].split("."))

        latest_version = tuple(
                re_version.match(self.get_latest_release_version())["version"].split("."))

        return latest_version > current_version

 
def run_tests():
    print("Tests have been moved to a separate directory")
    
if __name__ == '__main__':
    run_tests()
else:
    config = Config()

#logger.info("exiting module")

