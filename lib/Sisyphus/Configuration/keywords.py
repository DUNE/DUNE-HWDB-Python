#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author: 
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

# Dictionary keys for Configuration
# The purpose of these is so that if you misspell one of these keyname
# constants, Python will notice right away that it does not exist,
# whereas if you used a string and misspelled it, Python wouldn't notice
# until it actually looked for that key.

KW_ACTIVE_PROFILE = "active profile"
KW_PROFILES = "profiles"

KW_RESTAPI = "rest api"
KW_RESTAPI_NAME = "rest api name"
KW_USERS = "users"
KW_RESTAPI_EDITABLE = "rest api editable"
KW_DELETABLE = "deletable"
KW_SERVERS = "servers"
KW_DEVELOPMENT = "development"
KW_PRODUCTION = "production"
KW_TEST = "test"

KW_AUTHENTICATION = "authentication"
KW_AUTH_TYPE = "type"
KW_AUTH_HTGETTOKEN = "htgettoken"
KW_HTGETTOKEN_FLAGS = "flags"
KW_BEARER_TOKEN = "bearer token"
KW_VAULT_TOKEN = "vault token"
KW_AUTH_CERT = "certificate"
KW_CERT_TYPE = "certificate type"
KW_CERTIFICATE = "certificate"
KW_P12 = "p12"
KW_PEM = "pem"

KW_LOGGING = "logging"
KW_LOGLEVEL = "loglevel"

KW_SETTINGS = "settings"
