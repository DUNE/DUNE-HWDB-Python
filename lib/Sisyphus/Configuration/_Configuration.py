#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

# This module should NOT import anything else from this project that uses
# Config or uses anything that uses Config

from .exceptions import *
from .keywords import *

import Sisyphus # for version and some file paths
from Sisyphus.Utils.Terminal.Style import Style

import threading
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
from copy import deepcopy

import logging
import logging.config
from warnings import warn

RESTAPI_DEV = 'dbwebapi2.fnal.gov:8443/cdbdev'
RESTAPI_PROD = 'dbwebapi2.fnal.gov:8443/cdb'
DEFAULT_RESTAPI = RESTAPI_DEV
DEFAULT_RESTAPI_NAME = KW_DEVELOPMENT

MY_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__)))
USER_SETTINGS_DIR = os.path.normpath(os.path.expanduser("~/.sisyphus"))

USER_CONFIG_FILE = os.path.join(USER_SETTINGS_DIR, "config.json")
DEFAULT_LOG_CONFIG_FILE = os.path.join(MY_PATH, "default_log_config.py")
LOG_CONFIG_FILE = os.path.join(USER_SETTINGS_DIR, "log_config.py")

BEARER_TOKEN_FILENAME = 'bearer_token'
VAULT_TOKEN_FILENAME = 'vault_token'

###############################################################################
#
#  DEFAULT INITIAL CONFIGURATION
#  -----------------------------
#  When the application is first run, it checks ~/.sisyphus/config.json. If it
#  does not find it, it will create a new one. The new config.json will contain
#  a "development" and a "production" profile. Since we've changed over to 
#  using htgettoken for authentication, these profiles should be acceptable
#  out-of-the-box.
#
###############################################################################

NEW_CONFIG = {
    KW_ACTIVE_PROFILE: KW_DEVELOPMENT,
    KW_PROFILES: {
        KW_DEVELOPMENT: {
            KW_RESTAPI: RESTAPI_DEV,
            KW_RESTAPI_NAME: KW_DEVELOPMENT,
            KW_RESTAPI_EDITABLE: False, # Obviously, we can't stop anyone from
                        # going into the config file and editing this, but at
                        # least, any user interfaces that modify the config for
                        # the user should respect this. This is to prevent
                        # someone from having a profile named "development"
                        # point to production, or vice-versa.
            KW_DELETABLE: False, # Like above, some profiles should always
                        # exist and should not be able to be deleted.
            KW_AUTHENTICATION: {
                KW_AUTH_TYPE: KW_AUTH_HTGETTOKEN, # The alternate is 
                        # "certificate", which is deprecated. At some point in
                        # the future, certificates may not even work anymore.
                KW_HTGETTOKEN_FLAGS: [] # Additional flags to pass to
                        # htgettoken. The app already handles several of these,
                        # and it (currently) will *not* check to see if you
                        # are duplicating them here, so they should not be
                        # overriden.
                        #
                        # One possibly useful flag is "--web-open-command=",
                        # which forces htgettoken to not attempt to open a
                        # browser window.
            },
            KW_USERS: {}, # For a profile that uses a certificate, it doesn't
                        # make sense to have a "users" node, since there's only
                        # one user for a certificate. But, using the new token
                        # method, there's nothing keeping multiple users from
                        # using the same profile, but logging in with different
                        # credentials. So, for any settings that are user-
                        # specific (e.g., what email addresses to use), they
                        # should be stored here.
                        #
                        # Of course, this requires an actual call to whoami in
                        # the REST API, so the Configuration module should NOT
                        # try to do anything with this *automatically in
                        # anything that happens when Configuration is imported.
                        # Just loading the Configuration module alone (e.g., to
                        # get a logger) should not have the overhead of an API 
                        # call.
            KW_SETTINGS: {
                KW_EXTRA_KWARGS: { # Extra kwargs for requests
                    'verify': True,
                        # There's a bug in Requests 2.32 that causes a 
                        # segmentation fault when used in a multithreaded
                        # application when using certificates. Setting
                        # 'verify' to False makes it go away. Since we're
                        # using a header provided by htgettoken now, we can
                        # set this to True. (Alternatively, it could be 
                        # omitted altogether.) However, if we ever need to
                        # revert to certificates, you will probably need
                        # to set this to False again.
                },
                KW_THROTTLE_LOCK: False, # Setting this to True will cause
                        # the RestApiV1 module to use a threading.Lock()
                        # object to restrict REST API calls to only one
                        # thread at a time. (I.e., multiple threads may
                        # still be created and used, but only one will be
                        # permitted in the code block that makes the
                        # request.) If this parameter is omitted, a
                        # default value of False will be used.
                KW_LOG_HEADERS: False, # Setting this to True will cause
                        # the RestApiV1 module to explicitly prepare requests 
                        # before sending them, so that the exact content of
                        # the header and body of the request can be logged.
                        # Useful if you need to see exactly what is being sent.
                KW_LOG_REQUEST_JSON: False, # If the request includes a 'json'
                        # parameter, log its contents. Useful for checking
                        # what is actually in the request, but it does clutter
                        # the logs a bit.
                KW_TIMEOUTS: (5, 10, 15, 30, 60), # The number of times to
                        # retry a request if the request times out, and the
                        # length of each timeout
            }
        },
        KW_PRODUCTION: {
            # The same comments for the "development" profile apply here. Keys
            # that have useful default values are omitted. See the 
            # "development" profile for extra options, if needed.
            KW_RESTAPI: RESTAPI_PROD,
            KW_RESTAPI_NAME: KW_PRODUCTION,
            KW_RESTAPI_EDITABLE: False,
            KW_DELETABLE: False,
            KW_AUTHENTICATION: {
                KW_AUTH_TYPE: KW_AUTH_HTGETTOKEN,
            },
            KW_USERS: {},
            KW_SETTINGS: {},
        }
    },
    KW_SERVERS: {       # Just a list of available servers. This is used in 
                        # Sisyphus.Gui.Configuration to give the user a set of
                        # choices to use for a new profile.
        KW_DEVELOPMENT: RESTAPI_DEV,
        KW_PRODUCTION: RESTAPI_PROD,
        #KW_TEST: RESTAPI_DEV,   # It's probably never going to happen, but I
                        # think there should be a 'test' server that should be
                        # used by consortia to test their setups, instead of
                        # using 'development', which could change at any moment
                        # if Fermilab is actively working on the REST API.
    }
}

###############################################################################
#
#  DEFAULT NEW PROFILE
#  -------------------
#  This is a template for creating a new profile, as is done in
#  Sisyphus.Gui.Configuration
#

NEW_PROFILE = {
    KW_RESTAPI_NAME: DEFAULT_RESTAPI_NAME,
    KW_RESTAPI: DEFAULT_RESTAPI,
    KW_RESTAPI_EDITABLE: True,
    KW_DELETABLE: True,
    KW_AUTHENTICATION: {
        KW_AUTH_TYPE: KW_AUTH_HTGETTOKEN,
        KW_HTGETTOKEN_FLAGS: []
    },
    KW_USERS: {},
    KW_SETTINGS: {
        KW_EXTRA_KWARGS: {
            'verify': False,
        }
    }
}

###############################################################################

class Profile:
    '''represents a node under 'profiles' in the Config object

    Added 12 April 2025
    Don't create this directly. Let the Config class do it.

    This class was created to fill the possible need that an application
    might need to operate under two different profiles at the same time.
    So, the RestApiV1 module is being expanded to permit one to pass a 
    profile to any function instead of every function just using the 
    active profile under config.
    
    '''

    _cache = {}
    _class_lock = threading.Lock()

    def __new__(cls, parent, profile_name, profile_data):

        # Create a key for the cache. When multiple requests are made
        # for the same key, just return the same object each time.
        # I didn't include 'parent' because... I can't imagine anyone
        # having two different config objects that point to the same
        # profile object.
        key = (profile_name, id(profile_data))
        with cls._class_lock:
            if key in cls._cache:
                return cls._cache[key]
            else:
                new_obj = super().__new__(cls)
                cls._cache[key] = new_obj
                setattr(new_obj, '_initialized', False)
                return new_obj

    def __init__(self, parent, profile_name, profile_data):

        # If we're being served up an instance from the cache, it's still
        # going to try to __init__ it. So, we have to check if it's already
        # initialized and leave it alone if it is
        with self.__class__._class_lock:
            if self._initialized:
                return
                
            self._profile_name = profile_name
            self.profile_data = profile_data
            self._parent = parent
            self._initialized = True

    @property
    def config(self):
        return self._parent

    @property
    def profile_name(self):
        return self._profile_name
            
    @property 
    def authentication(self):
        try:
            return self.profile_data.get(KW_AUTHENTICATION, None)
        except KeyError:
            raise ConfigurationError(f"{KW_AUTHENTICATION!r} not set in profile "
                            f"{self._profile_name}")

    @property
    def rest_api(self):
        try:
            return self.profile_data[KW_RESTAPI]
        except KeyError:
            raise ConfigurationError(f"{KW_RESTAPI!r} not set in profile {self._profile_name}")
    
    @property
    def settings(self):
        return self.profile_data.get(KW_SETTINGS, {})
    
    # bearer_token_file and vault_token_file are not configurable at this time
    @property
    def bearer_token_file(self):
        return os.path.join(self.profile_dir, BEARER_TOKEN_FILENAME)
    
    @property
    def vault_token_file(self):
        return os.path.join(self.profile_dir, VAULT_TOKEN_FILENAME)

    @property
    def profile_dir(self):
        pd = os.path.join(self.config.user_settings_dir, self.profile_name)
        os.makedirs(pd, mode=0o700, exist_ok=True)
        return pd
    
class Config:
    def __init__(self, *, 
            user_settings_dir=None, user_config_file=None, log_config_file=None, args=sys.argv):
        #{{{
        self.original_args = args

        self.user_config_file = (user_config_file or USER_CONFIG_FILE)
        self.log_config_file = (log_config_file or LOG_CONFIG_FILE)
        self.user_settings_dir = (user_settings_dir or USER_SETTINGS_DIR)

        self.logger = self.getLogger(__name__)
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
            if self.active_profile.profile_data[KW_LOGLEVEL] is not None:
                logger.setLevel(self.active_profile.profile_data[KW_LOGLEVEL])
        
        #if not already_loaded:
        #    logger.debug(f"created logger '{name}'")
        
        return logger
        #}}}

    def load_additional_config(self, filename, recopy_if_missing=True, recopy_on_error=False):
        #{{{
        filepath = os.path.join(self.user_settings_dir, filename)

        def load_config():
            with open(filepath, 'r') as fp:
                raw_data = fp.read()

                _locals, _globals = {}, {}
                exec(raw_data, _globals, _locals)
            
            return _locals["contents"]

        def reset_config():
            default_filename = f"default_{filename}"
            try:
                src_file = os.path.join(MY_PATH, default_filename)
                with open(src_file, "r") as f:
                    raw_data = f.read()
            except Exception:
                msg = f"The configuration file at '{src_file}' could not be read."
                raise ConfigurationError(msg)

            raw_data = raw_data.replace("${SISYPHUS_VERSION}", Sisyphus.version)

            try:
                with open(filepath, "w") as fp:
                    fp.write(raw_data)
                os.chmod(filepath, mode=0o600)
            except Exception:
                msg = f"The config file '{filepath}' could not be created."
                raise ConfigurationError(msg)

        try:
            config = load_config()
        except Exception as exc:
            if (type(exc) is FileNotFoundError and recopy_if_missing) or recopy_on_error:
                reset_config()
                config = load_config()
            else:
                raise exc

        return config
        #}}}
            
    def _init_logging(self):
        #{{{ 
        # We need to create the directory the logs will be written to
        try:
            path = os.path.dirname(self.log_config_file)
            os.makedirs(path, mode=0o700, exist_ok=True) 
        except Exception:
            msg = f"Could not create the log directory at {path}"
            raise ConfigurationError(msg)
   
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
                raise ConfigurationError("log config is obsolete")

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
   
    def get_profile(self, profile_name):
        return Profile(self, profile_name, self.config_data[KW_PROFILES][profile_name])
    
    @property
    def active_profile(self):
        active_profile_name = self.config_data[KW_ACTIVE_PROFILE]
        return self.get_profile(active_profile_name)

    @property
    def settings(self):
        return self.config_data.get(KW_SETTINGS, {})

    @property
    def bearer_token(self):
        return self.active_profile.get(KW_BEARER_TOKEN, BEARER_TOKEN_FILE)


    def _extract_cert_info(self):
        #{{{
        self.logger.debug("Extracting certificate information")
        active_profile = self.active_profile            
        self.cert_has_expired = None
        self.cert_expires = None
        self.cert_fullname = None
        self.cert_username = None
        self.cert_days_left = None
        
        if active_profile.authentication.get(KW_CERTIFICATE, None) is None:
            self.logger.debug("There is no certificate to extract data from.")
            return 
        if self.cert_type == KW_P12:       
            self.logger.debug("Unable to extract data from P12 certificate without password")
            return 

 
        with open(active_profile.authentication[KW_CERTIFICATE], "r") as fp:
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
        self.config_data = deepcopy(NEW_CONFIG)
                 
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
                raise ConfigurationError(msg)

        # If we started from a p12 file and extracted a certificate, save the certificate
        if hasattr(self, 'temp_pem_file'):
            perm_filename = os.path.join(self.user_settings_dir, f"certificate_{self.profile_name}.pem")
            shutil.copyfile(self.temp_pem_file.name, perm_filename)
            self.active_profile[KW_CERTIFICATE] = perm_filename
            del self.temp_pem_file
               
        # Save the config file
        try:
            with open(self.user_config_file, "w") as f:
                f.write(json.dumps(self.config_data, indent=4))
            os.chmod(self.user_config_file, mode=0o600)
        except Exception:
            msg = "The configuration file could not be created."
            raise ConfigurationError(msg)
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
            raise ConfigurationError(f"Unable to extract pem certificate from p12 file: "
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
        
        # Check what profile they're trying to use
        if [self.args.profile is not None, self.args.dev, self.args.prod].count(True) > 1:
            err_msg = "Error: --dev, --prod, and --profile are mutually exclusive" 
            self.logger.error(err_msg)
            raise ConfigurationError(err_msg)
        else:
            if self.args.profile is not None:
                override_profile = self.args.profile
            elif self.args.dev:
                override_profile = KW_DEVELOPMENT
            elif self.args.prod:
                override_profile = KW_PRODUCTION
            else:
                override_profile = None
        
        if override_profile is not None and override_profile != self.config_data[KW_ACTIVE_PROFILE]:
            # Override the 'active profile' with the profile given, if it exists
            if override_profile not in self.config_data.get(KW_PROFILES, {}):
                raise ConfigurationError(f"profile {self.args.profile} does not exist.")

            self.config_data[KW_ACTIVE_PROFILE] = override_profile
            self.logger.debug(f"active profile overridden to '{self.args.profile}'")
        else: 
            self.logger.debug(f"using active profile '{self.active_profile}'")
        
        active_profile = self.active_profile
    
        # set the log level (which will be effective only AFTER config initializes, so there
        # will be some initial info or debug messages even if level is set higher)
        log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'default']
        if self.args.loglevel is not None:
            if self.args.loglevel not in log_levels:
                err_msg = f"Error: --loglevel must be in {log_levels}"
                self.logger.error(err_msg)
                raise ConfigurationError(err_msg)
            else:
                if self.args.loglevel != 'default':
                    self.active_profile.profile_data[KW_LOGLEVEL] = self.args.loglevel
                else:
                    active_profile.profile_data[KW_LOGLEVEL] = None
        else:
            active_profile.profile_data[KW_LOGLEVEL] = active_profile.profile_data.get(KW_LOGLEVEL, None)

        self.logger.info(f"using rest api '{active_profile.profile_data[KW_RESTAPI]}'")
        
        # NOTE: 14 April 2025
        # +++++++++++++++++++
        # The code has changed and the notes below may or may not still apply
        #
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
            active_profile.authentication[KW_AUTH_TYPE] = KW_CERTIFICATE
            if self.args.cert_type is not None:
                if self.args.cert_type.lower() in (KW_P12, "pem"):
                    args_cert_type = self.args.cert_type.lower()
                else:
                    raise ConfigurationError("Error: certificate type must be 'pem' or 'p12'")
            elif self.args.cert.lower().endswith(KW_P12):
                args_cert_type = KW_P12
            elif self.args.cert.lower().endswith(KW_PEM):
                args_cert_type = KW_PEM
            else:
                raise ConfigurationError("Error: certificate type must be 'pem' or 'p12'")
            
            active_profile.authentication[KW_CERTIFICATE] = self.args.cert
            active_profile.authentication[KW_CERT_TYPE] = args_cert_type
        else:
            if self.args.cert_type is not None:
                raise ConfigurationError("Error: certificate type provided, but no certificate")
            active_profile.authentication.get(KW_CERTIFICATE, None)
            active_profile.authentication.get(KW_CERT_TYPE, None)
            
        if (active_profile.authentication.get(KW_CERT_TYPE) == KW_PEM 
                                        and self.args.password is not None):
            raise ConfigurationError("Error: passwords cannot be used with pem certificates")
        
        active_profile.authentication.get(KW_CERTIFICATE, self.args.cert)
        
        # Now the hard part. If it's a p12 with a password, we should convert to pem.
        #if active_profile.profile_data.authentication[KW_CERT_TYPE] == KW_P12:
        #if active_profile.profile_data.authentication[KW_AUTH_TYPE] == KW_AUTH_HTGETTOKEN:
        if self.args.cert is not None:
            if active_profile.authentication[KW_CERT_TYPE] == KW_P12:
                if self.args.password is not None:
                    self.logger.debug("extracting PEM certificate from P12")

                    self._extract_pem(
                            active_profile.authentication[KW_CERTIFICATE], 
                            self.args.password)

                    active_profile.authentication[KW_CERT_TYPE] = KW_PEM
                    active_profile.authentication[KW_CERTIFICATE] = self.temp_pem_file.name
                else:
                    self.logger.debug("Using P12 certificate, but no password was supplied")
            else:
                self.logger.debug("using PEM certificate")

        # If they provided --htgettoken, we need to explicitly change the auth type back
        if self.args.htgettoken:
            active_profile.authentication[KW_AUTH_TYPE] = KW_HTGETTOKEN
        #}}}
    
    def _load_config(self, filename):
        #{{{
        # open the file
        try:
            with open(filename, "r") as f:
                raw_data = f.read()
        except Exception:
            self.config_data = deepcopy(NEW_CONFIG)
            return
        
        # parse it as JSON5
        try:
            self.config_data = json5.loads(raw_data)
        except Exception as ex:
            raise ConfigurationError(f"'{filename}' was not a valid JSON/JSON5 file --> {ex}")

        # Let's check for a new version, but don't do it more than once per day
        today = datetime.now().date().strftime("%Y-%m-%d")
        if self.config_data.get("version", None) is not None:
            if self.config_data["version"].get("last checked", "1776-07-04") >= today:
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
        group.add_argument('--dev',
                            dest='dev',
                            action='store_true',
                            required=False,
                            help=f'shortcut for "--profile=development"')
        group.add_argument('--prod',
                            dest='prod',
                            action='store_true',
                            required=False,
        group.add_argument('--profile',
                            dest='profile',
                            metavar='<profile-name>',
                            required=False,
                            help="Use the profile named <profile-name>.")
        group.add_argument('--loglevel',
                            dest='loglevel',
                            metavar='<loglevel>',
                            required=False,
                            help="Only log messages at <loglevel> or higher in severity. "
                                "(DEBUG, INFO, WARNING, ERROR, CRITICAL, or 'default' to "
                                "use the default level")    
        group.add_argument('--htgettoken',
                            dest='htgettoken',
                            action='store_true',
                            required=False,
                            help="Use htgettoken authentication. (This is the default. "
                                "If you've changed your authentication to 'cert', use "
                                "this to set it back to 'htgettoken'.")
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
            raise ConfigurationError(msg)

        raw_data = raw_data.replace("${SISYPHUS_VERSION}", Sisyphus.version)

        try:
            with open(self.log_config_file, "w") as f:
                f.write(raw_data)
            os.chmod(self.log_config_file, mode=0o600)
        except Exception:
            msg = "The logging config file could not be created."
            raise ConfigurationError(msg)
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

