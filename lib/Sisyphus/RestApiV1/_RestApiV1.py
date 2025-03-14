#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/RestApiV1/_RestApiV1.py
Copyright (c) 2024 Regents of the University of Minnesota
Author: 
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
    Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.Utils.Terminal.Style import Style
import sys

import Sisyphus.Configuration as Config # for keywords
from .exceptions import *
from .keywords import *

from copy import deepcopy
import json
import requests
import urllib.parse
import functools
import threading
import time
import subprocess
import os
#import faulthandler
#faulthandler.enable()
from contextlib import nullcontext

# Define any key/value pairs here that you wish to add to all session
# requests by default.
# Example: to set requests to timeout after 10 seconds, add 
#     session_kwargs['timeout'] = 10
# (Don't add it here. Just set it after loading this module.) 
session_kwargs = {}
#session_kwargs['log_headers'] = True

# A hack for Requests 2.32
# If using requests in a multithreaded fashion, the app will sometimes
# seg fault when using certificates. For some reason, the problem goes
# away if you disable 'verify' with requests
# The default behavior right now will be to disable 'verify', even 
# though this is highly NOT RECOMMENDED. It throws a bunch of warnings
# when you do this, so we have to use a warning handler to squelch it.
if config.settings.get("disable_host_certificate_verification", True):
    session_kwargs["verify"] = False
import warnings
import urllib3
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)


# A second hack for Requests 2.32
# A different way to avoid seg faults is to just allow only one thread
# process requests at a time
if config.settings.get("use_throttle_lock", False):
    throttle_lock = threading.Lock()
else:
    throttle_lock = nullcontext()

# Use this function when constructing a URL that uses some variable as 
# part of the URL itself, e.g.,
#    path = f"api/v1/components/{sanitize(part_id)}"
# DON'T use this function for paramters at the end of the URL if you're 
# using "params" to pass them, because the session.get() method will 
# do that for you, and doing it twice messes up things like postgres wildcards.
def sanitize(s, safe=""):
    return urllib.parse.quote(str(s), safe=safe)

# Use this lock to prevent multiple threads from trying to refresh
# the bearer token at the same time. If multiple threads tried to 
# refresh, and each one tried to bring up a browser window, that would
# be a problem. But once one of the threads has come back from the 
# browser window, the other threads' attempts would succeed without
# needing to bring up a browser window.
authentication_lock = threading.Lock()

log_lock = threading.Lock()
log_request_json = True

# Something happened with Python 3.12 with the GIL that caused seg faults when
# multiple threads shared the same session object. To mitigate this, every time
# one needs a session, one should request one by calling get_session(). It will
# create a session for each thread and put it in threading.local(). Hopefully,
# once the thread is done, the session will be garbage collected along with the
# thread.

thread_local = threading.local()
bearer_header = None
def get_session(use_config=config):

    if not hasattr(thread_local, "session") or use_config is not None:
        if use_config is None:
            use_config = config
        logger.info(f"CREATING session for thread {threading.current_thread().name}")
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
        session.mount(f'https://{config.rest_api}', adapter)

        if use_config.authentication == 'certificate':
            logger.info("authentication for this session will be 'certificate'")
            session.cert = use_config.certificate
        else:
            logger.info("authentication for this session will be 'token'")

        thread_local.session = session
        thread_local.authentication = use_config.authentication

    else:
        logger.info(f"REUSING session for thread {threading.current_thread().name}")

    return thread_local.session, thread_local.authentication

#-----------------------------------------------------------------------------

_refresh_required = True
def refresh_token():
    global thread_local
    global bearer_header

    def do_refresh():
        global _refresh_required

        config_dir = Config.USER_SETTINGS_DIR
        vault_token_file = Config.VAULT_TOKEN_FILE
        bearer_token_file = Config.BEARER_TOKEN_FILE

        tokens = [
            'htgettoken',
            '-q',
            f'--configdir={config_dir}',
            f'--vaulttokenfile={vault_token_file}',
            f'--outfile={bearer_token_file}',
            f'--vaultserver=htvaultprod.fnal.gov',
            f'--issuer=fermilab'
        ]

        refresh_subprocess = subprocess.Popen(
                                tokens,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        refresh_subprocess.wait(timeout=120)        


        if refresh_subprocess.returncode != 0:
            raise RuntimeError("Unable to refresh authentication token. "
                            "(Have you installed htgettoken?)")
        _refresh_required = False

    logger.debug("Attempting to refresh token")
    with authentication_lock:
        if _refresh_required:

            do_refresh()
            bearer_header = None

            logger.debug("Finished refreshing token")
        else:
            logger.debug("Token already refreshed by another thread (?)")
            

#-----------------------------------------------------------------------------

class retry:
    #{{{
    '''Wrapper for RestApi functions to permit them to retry on a connection failure'''

    #def __init__(self, retries=1, timeouts=(None, None, None, None, None) ):
    def __init__(self, retries=None, timeout=None, timeouts=None ):
        # You can either specify the number of retries and an optional 
        # timeout, or you can specify a list/tuple of the timeouts to use 
        # on each try. If you specify timeouts, then retries will be ignored 
        # and calculated from the timeouts list. If you specify retries
        # and NOT timeouts, then timeouts will be initialized as the timeout
        # value repeated <retries> times. A timeout of None means don't
        # use a specific timeout on that try.

        self.default_timeouts = timeouts

        if timeouts is not None:
            self.default_retries = len(timeouts)
            self.timeouts = tuple(timeouts)
        else:
            self.default_retries = retries or 1
            self.timeouts = (timeout,) * self.default_retries

    def __call__(self, function):

        @functools.wraps(function)
        def wrapped_function(*args, **kwargs):
            global _refresh_required

            timeouts = kwargs.pop("timeouts", None)
            retries = kwargs.pop("retries", None)
            timeout = kwargs.pop("timeout", None)

            if timeouts is not None:
                retries = len(timeouts)
                timeouts = tuple(timeouts)
            elif retries is not None:
                timeouts = (timeout,) * retries
            else:
                retries = self.default_retries
                timeouts = self.default_timeouts

            last_err = None
            default_timeout = kwargs.get('timeout', None)
            logger.debug(f"Wrapper function is assigned {retries} retries")
            for try_num in range(retries):
                try:
                    if type(last_err) is ExpiredSignature:
                        _refresh_required = True
                        logger.debug("Signature expired. Must refresh.")
                        refresh_token()
                except Exception as exc:
                    logger.error(f"Failed to refresh token: {exc}")

                try:
                    if timeouts[try_num]:
                        kwargs['timeout'] = timeouts[try_num]
                    elif default_timeout:
                        kwargs['timeout'] = default_timeout
                    else:
                        kwargs.pop('timeout', None)

                    if threading.current_thread().name == "MainThread":
                        s = ("[connecting]" if try_num == 0 
                                        else f"[connection failed. retrying: {try_num}]")
                        msg = "".join([ 
                                Style.cursor_abs_horizontal(1),
                                Style.debug(f'{s}'),
                                Style.erase_right
                            ])

                        sys.stdout.write(msg)
                        sys.stdout.flush()

                    resp = function(*args, **kwargs)

                    break
                except ConnectionFailed as err:
                    msg = (f"Connection failure in '{function.__name__}' "
                            f"in thread '{threading.current_thread().name}' "
                            f"(attempt #{try_num+1})")
                    logger.warning(msg)
                    last_err = err
                except ExpiredSignature as err:
                    msg = (f"Signature expired while calling {function.__name__} "
                            f"in thread '{threading.current_thread().name}' "
                            f"(attempt #{try_num+1})")
                    logger.warning(msg)
                    last_err = err
                except Exception as exc:
                    msg = (f"General exception '{exc}' while calling {function.__name__} "
                            f"in thread '{threading.current_thread().name}' "
                            f"(attempt #{try_num+1})")
                    logger.error(msg)
                    last_err = exc
                    raise


                finally:
                    if threading.current_thread().name == "MainThread":
                        msg = "".join([
                                Style.cursor_abs_horizontal(1),
                                Style.erase_line
                            ])

                        sys.stdout.write(msg)
                        sys.stdout.flush()
            else:
                logger.error(f"{msg}, max attempts reached")
                raise last_err

            return resp

        return wrapped_function
    #}}}

#-----------------------------------------------------------------------------

#@retry(retries=5, timeouts=(5, 10, 15, 20, 25))
@retry(timeouts=(5, 10, 15, 30, 60, 60))
def _request(method, url, *args, return_type="json", **kwargs):
    #{{{
    '''Does a session.request() with some extra error handling

    "Master" function for all gets, posts, and patches. If the return
    type is "json" (which is the default), it will enforce that the 
    response is a valid JSON dictionary that contains a "status" of 
    "OK" otherwise.

    Raises
    ------
    NameResolutionFailure
            The "get" returned a ConnectionError that is most likely
            due to not being able to resolve the URL.
    
    ConnectionFailed
            The "get" returned a ConnectionError for other reasons
    
    InvalidResponse
            The server returned something that wasn't JSON, or wasn't a
            dictionary, or the dictionary not have a "status"

    DatabaseError
            The server returned a valid response, but returned a
            status other than "OK"

    CertificateError
            The certificate was invalid or expired.

    BadSpecificationFormat
            The data provided for the Item Specification or Test Results
            does not conform to the specification or test definition.

    InsufficientPermissions
            The user does not have adequate authority for this request.

    ExpiredSignature
            The bearer token has expired 
            (new authentication system, March 2025)
    
    '''
    global bearer_header

    threadname = threading.current_thread().name
    msg = (f"<_request> [{method.upper()}] "
            f"url='{url}' method='{method.lower()}'")
    with log_lock:
        logger.debug(msg) 

    if log_request_json and "json" in kwargs:
        try:
            msg = f"json =\n{json.dumps(kwargs['json'], indent=4)}"
        except json.JSONDecodeError as exc:
            msg = f"data =\n{kwargs['json']}"
        with log_lock:
            logger.debug(msg)


    session, authentication = get_session()

    if authentication == 'token' and bearer_header is None:
        try:
            with open(config.bearer_token, 'r') as fp:
                contents = fp.read().strip()
                bearer_header = {'Authorization': f'Bearer {contents}'}
        except FileNotFoundError as err:
            _refresh_required = True
            refresh_token()
            with open(config.bearer_token, 'r') as fp:
                contents = fp.read().strip()
                bearer_header = {'Authorization': f'Bearer {contents}'}
    else:
        bearer_header = {}

    #
    #  Send the "get" request and handle possible errors
    #
    augmented_kwargs = {**session_kwargs, **kwargs}
        
    extra_info = \
    [
        "Additional Information:",
        f"| thread: {threadname}",
        f"| url: {url}",
        f"| method: {method}",
        f"| args: {args}, kwargs: {augmented_kwargs}",
    ]
    
    log_headers = augmented_kwargs.pop("log_headers", False)
    
    try:
        if log_headers:
            verify = augmented_kwargs.pop('verify', True)
            timeout = augmented_kwargs.pop('timeout', True)
            req = requests.Request(method, url, *args, **augmented_kwargs)
            prepped = req.prepare()

            with log_lock:
                logger.info(f"prepped.headers: {prepped.headers}")
                if prepped.body is not None and len(prepped.body) > 1000:
                    logger.info(f"prepped.body (beginning): {prepped.body[:800]}")
                    logger.info(f"prepped.body (end): {prepped.body[-200:]}")
                else:
                    logger.info(f"prepped.body: {prepped.body}")


            with throttle_lock:
                resp = session.send(prepped)

        else:
            with throttle_lock:
                augmented_kwargs['headers'] = {
                        **augmented_kwargs.get('headers', {}),
                        **bearer_header
                }
                resp = session.request(method, url, *args, **augmented_kwargs)


    except requests.exceptions.ConnectionError as conn_err:
        extra_info.append(f"| exception: {repr(conn_err)}")
        if "[Errno -2]" in str(conn_err):
            msg = ("The server URL appears to be invalid.")
            with log_lock:
                logger.error(msg)
                logger.info('\n'.join(extra_info))
            raise NameResolutionFailure(msg) from None
        elif "[Errno -3]" in str(conn_err):
            msg = ("The server could not be reached. Check your internet connection.")
            with log_lock:
                logger.error(msg)
                logger.info('\n'.join(extra_info))
            raise ConnectionFailed(msg) from None
        else:
            msg = ("A connection error occurred while attempting to retrieve data from "
                     f"the REST API.")
            with log_lock:
                logger.error(msg)
                logger.info('\n'.join(extra_info))
            raise ConnectionFailed(msg) from None
    except requests.exceptions.ReadTimeout as timeout_err:
        extra_info.append(f"| exception: {repr(timeout_err)}")
        msg = ("A read timeout error occurred while attempting to retrieve data from "
                 f"the REST API.")
        with log_lock:
            logger.error(msg)
            logger.info('\n'.join(extra_info))
        raise ConnectionFailed(msg) from None
    except Exception as exc:
        extra_info.append(f"| exception: {repr(exc)}")
        msg = ("An unhandled error occurred while attempting to retrieve data from "
                 f"the REST API.")
        with log_lock:
            logger.error(msg)
            logger.info('\n'.join(extra_info))


    #extra_info.append(f"| request headers: {resp.request.headers}")
    extra_info.append(f"| status code: {resp.status_code}")
    extra_info.append(f"| elapsed: {resp.elapsed}")
    if log_headers:
        extra_info.append(f"| response headers: {resp.headers}")
    if resp.encoding == "utf-8":
        extra_info.append(f"| response: {resp.text}")
    else:
        extra_info.append(f"| response: [binary]")
    #logger.debug('\n'.join(extra_info))


    if return_type.lower() == "json":
        #  Convert the response to JSON and return.
        #  If the response cannot be converted to JSON, raise an exception
        try:
            resp_json = deepcopy(resp.json())
        except json.JSONDecodeError as json_err:
            # This is probably a 4xx or 5xx error that returned an HTML page 
            # instead of JSON. These are hard to figure out until we actually
            # encounter them and look for some distinguishing characteristics,
            # but we'll do what we can.
            if "The SSL certificate error" in resp.text:
                msg = "The certificate was not accepted by the server."
                with log_lock:
                    exc_type = CertificateError
                    logger.error(msg)
                    extra_info.append(f"| exc_type: {exc_type.__name__}")
                    logger.info('\n'.join(extra_info))
                raise exc_type(msg) from None    
        
            else:
                msg = "The server response was not valid JSON. Check logs for details."
                with log_lock:
                    exc_type = InvalidResponse
                    logger.error(msg)
                    extra_info.append(f"| exc_type: {exc_type.__name__}")
                    logger.info('\n'.join(extra_info))
                raise exc_type(msg) from None

        #  Look at the response and make sure it complies with the expected
        #  data format and does not indicate an error.
        if type(resp_json) == dict and resp_json.get(KW_STATUS, None) == KW_STATUS_OK:
            return resp_json

        #  Now we know we're going to have to raise an exception, but let's
        #  try to be more specific.
        if type(resp_json) != dict or KW_STATUS not in resp_json:
            msg = "The server response was not valid. Check logs for details."
            exc_type = InvalidResponse
            with log_lock:
                logger.error(msg)
                extra_info.append(f"| exc_type: {exc_type.__name__}")
                logger.info('\n'.join(extra_info))
            raise exc_type(msg) from None

        if KW_DATA in resp_json:
            database_errors = \
            [
                {
                    "signature": "The test specifications do not match the "
                                   "test type definition!",
                    "message": "The Test Results format does not match the "
                                 "test type definition",
                    "exc_type": BadSpecificationFormat,
                },
                {
                    "signature": "A 'specifications' object matching the "
                                    "ComponentType difinition is required!",
                    "message": "The specifications format does not match the "
                                 "definition for the component type",
                    "exc_type": BadSpecificationFormat,
                },
                {
                    "signature": "The input specifications do not match the "
                                    "component type definition",
                    "message": "The specifications format does not match the "
                                 "definition for the component type",
                    "exc_type": BadSpecificationFormat,
                },
                {
                    "signature": "Not authorized",
                    "message": "The user does not have the authority for this request",
                    "exc_type": InsufficientPermissions,
                },
                {
                    "signature": "Verification failed: JWT decode failed "
                                "ExpiredSignatureError('Signature has expired')",
                    "message": "The user's token has expired",
                    "exc_type": ExpiredSignature,
                },
            ]
            
            for database_error in database_errors:
                if (database_error["signature"] in resp_json['data']):
                    msg = database_error["message"]
                    exc_type = database_error["exc_type"]
                    with log_lock:
                        logger.error(msg)
                        extra_info.append(f"| exc_type: {exc_type.__name__}")
                        logger.info('\n'.join(extra_info))
                    raise exc_type(msg)

        if KW_ERRORS in resp_json and type(resp_json[KW_ERRORS]) is list:
            msg_parts = []
            for error in resp_json[KW_ERRORS]:
                if ("loc" in error 
                        and type(error["loc"]) is list 
                        and len(error["loc"]) > 0
                        and "msg" in error):
                    msg_parts.append(f"{error['loc'][0]} -> {error['msg']}")
            msg = f"Bad request format: {', '.join(msg_parts)}"
            with log_lock:
                exc_type = BadDataFormat
                logger.error(msg)
                extra_info.append(f"| exc_type: {exc_type.__name__}")
                logger.info('\n'.join(extra_info))
            raise exc_type(msg)


        # Fallthrough if no other conditions raised an error
        msg = "The server returned an error. Check logs for details."
        with log_lock:
            exc_type = DatabaseError
            logger.error(msg)
            logger.info('\n'.join(extra_info))
        raise exc_type(msg, resp_json) from None
    else:
        with log_lock:
            logger.debug("returning raw response object")
        return resp
    #}}}

#-----------------------------------------------------------------------------

def _get(url, *args, **kwargs):
    return _request("get", url, *args, **kwargs)

#-----------------------------------------------------------------------------

def _post(url, data, *args, **kwargs):
    return _request("post", url, json=data, *args, **kwargs)

#-----------------------------------------------------------------------------

def _patch(url, data, *args, **kwargs):
    return _request("patch", url, json=data, *args, **kwargs)

##############################################################################
#
#  IMAGES
#
##############################################################################

def get_hwitem_image_list(part_id, **kwargs):
    #{{{
    logger.debug(f"<get_hwitem_images>")
    path = f"api/v1/components/{sanitize(part_id)}/images"
    url = f"https://{config.rest_api}/{path}"

    resp = _get(url, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def post_hwitem_image(part_id, data, filename, **kwargs):
    #{{{
    """Add an image for an Item"""
    
    logger.debug(f"<post_hwitem_image> part_id={part_id}, filename={filename}")
    path = f"api/v1/components/{sanitize(part_id)}/images"
    url = f"https://{config.rest_api}/{path}"

    with open(filename, 'rb') as fp:
        files = {
                **{key: (None, value) for key, value in data.items()},
                "image": fp
        }
        resp = _request("post", url, 
                json=data, files=files, 
                **kwargs)

    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_component_type_image_list(part_type_id, **kwargs):
    #{{{
    logger.debug(f"<get_component_images>")
    path = f"api/v1/component-types/{part_type_id}/images"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def post_component_type_image(part_type_id, image_payload, **kwargs):
    #{{{    
    """Add an image to a Component Type"""
    raise NotImplementedError("Coming soon!")
    #}}}

#-----------------------------------------------------------------------------


def get_test_image_list(part_id, test_id, **kwargs):
    #{{{
    """Get a list of images for a given test oid

    The oid represents a test record for a test type for an item.
    """
    logger.debug(f"<get_test_image_list> part_id={part_id}, test_id={test_id}")
    path = f"api/v1/components/{part_id}/tests/{test_type_id}/images"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    #}}}

#-----------------------------------------------------------------------------

def post_test_image(test_id, data, filename, **kwargs):
    #{{{
    """Add an image to a given test oid
    
    The oid represents a test record for a test type for an item.
    """
    raise NotImplementedError("Coming soon!")
    #}}}

#-----------------------------------------------------------------------------

def get_image(image_id, write_to_file=None, **kwargs):
    #{{{
    logger.debug(f"<get_image>")
    path = f"api/v1/img/{image_id}"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, return_type="raw", **kwargs)

    if write_to_file is not None:
        with open(write_to_file, "wb") as fp:
            fp.write(resp.content)

    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_hwitem_qrcode(part_id, write_to_file=None, **kwargs):
    #{{{
    logger.debug(f"<get_hwitem_qrcode> part_id={part_id}")
    path = f"api/v1/get-qrcode/{sanitize(part_id)}"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, return_type="raw", **kwargs)
    
    if write_to_file is not None:
        with open(write_to_file, "wb") as fp:
            fp.write(resp.content)

    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_hwitem_barcode(part_id, write_to_file=None, **kwargs):
    #{{{
    logger.debug(f"<get_hwitem_barcode> part_id={part_id}")
    path = f"api/v1/get-barcode/{sanitize(part_id)}"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, return_type="raw", **kwargs)
    
    if write_to_file is not None:
        with open(write_to_file, "wb") as fp:
            fp.write(resp.content)

    return resp
    #}}}


##############################################################################
#
#  HW ITEMS
#
##############################################################################

def get_hwitem(part_id, **kwargs):
    #{{{
    """Get an individual HW Item

    Response Structure:
        {
            "data": {
                "batch": null,
                "comments": "Here are some comments",
                "component_id": 150643,
                "component_type": {
                    "name": "jabberwock",
                    "part_type_id": "Z00100300030"
                },
                "country_code": "US",
                "created": "2024-01-25T06:25:36.709788-06:00",
                "creator": {
                    "id": 13615,
                    "name": "Alex Wagner",
                    "username": "awagner"
                },
                "status": {
                    "id": 1,
                    "name": "available"
                },
                "institution": {
                    "id": 186,
                    "name": "University of Minnesota Twin Cities"
                },
                "manufacturer": {
                    "id": 7,
                    "name": "Hajime Inc"
                },
                "part_id": "Z00100300030-00002",
                "serial_number": "SN3F958771",
                "specifications": [
                    {
                        "Color": "Red",
                        "Flavor": "Strawberry",
                    }
                ],
                "specs_version": 4
            },
            "link": {...},
            "methods": [...],
            "status": "OK"
        }
    """

    logger.debug(f"<get_hwitem> part_id={part_id}")
    path = f"api/v1/components/{sanitize(part_id)}"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs) 
    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_hwitems(part_type_id, *,
                page=None, size=None, fields=None, serial_number=None, part_id=None, **kwargs):
    #{{{
    logger.debug(f"<get_component_types> part_type_id={part_type_id},"
                f"page={page}, size={size}, fields={fields}, "
                f"serial_number={serial_number}, part_id={part_id}")
    path = f"api/v1/component-types/{sanitize(part_type_id)}/components"
    url = f"https://{config.rest_api}/{path}"

    params = []
    if page is not None:
        params.append(("page", page))
    if size is not None:
        params.append(("size", size))
    if serial_number is not None:
        params.append(("serial_number", serial_number))
    if part_id is not None:
        params.append(("part_id", part_id))
    ## *** currently broken in REST API
    if fields is not None:
        params.append(("fields", ",".join(fields)))

    resp = _get(url, params=params, **kwargs) 
    return resp
    #}}}

#-----------------------------------------------------------------------------

def post_hwitem(part_type_id, data, **kwargs):
    #{{{
    """Create a new Item in the HWDB

    Structure for "data":
        {
            "comments": <str>,
            "component_type": {"part_type_id": <str>},
            "country_code": <str>,
            "institution": {"id": <int>},
            "manufacturer": {"id": <int>},
            "serial_number": <str>,
            "specifications": {...},
            "subcomponents": {<str:func_pos>: <str:part_id>}
        }

        Structure of returned response:
        {
            "component_id": <int>,
            "data": "Created",
            "part_id": <str>,
            "status": "OK"
        }
    """

    logger.debug(f"<post_hwitem> part_type_id={part_type_id}")
    path = f"api/v1/component-types/{sanitize(part_type_id)}/components" 
    url = f"https://{config.rest_api}/{path}" 
    
    resp = _post(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def patch_hwitem(part_id, data, **kwargs):
    #{{{
    """Modify an Item in the HWDB

    Structure for "data":
        {
            "part_id": <str>,
            "comments": <str>,
            "manufacturer": {"id": <int>},
            "serial_number": <str>,
            "specifications": {...},
        }

    Structure of returned response:
        {
            "component_id": 44757,
            "data": "Created",
            "id": 151635,
            "part_id": "Z00100300001-00001",
            "status": "OK"
        }
    """

    logger.debug(f"<patch_hwitem> part_id={part_id}")
    path = f"api/v1/components/{sanitize(part_id)}" 
    url = f"https://{config.rest_api}/{path}"
    
    resp = _patch(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def post_bulk_hwitems(part_type_id, data, **kwargs):
    #{{{
    logger.debug(f"<post_bulk_hwitems> part_type_id={part_type_id}")
    path = f"api/v1/component-types/{sanitize(part_type_id)}/bulk-add"
    url = f"https://{config.rest_api}/{path}"
                
    resp = _post(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

# PROBABLY OBSOLETE
def patch_hwitem_enable(part_id, data, **kwargs):
    #{{{
    """Enables/disables an HWItem

    Structure for "data":
        {
            "comments": <str>,
            "component": {"part_id": <str>},
            "enabled": <bool>,
        }

    Structure of returned response:
        {
            "component_id": 44757,
            "data": "Created",
            "operation": "enabled",
            "part_id": "Z00100300001-00001",
            "status": "OK"
        }

    Note: at the time of this writing, "comments" overwrites the comment for
    the item itself!
    """
    logger.debug(f"<patch_hwitem_enable> part_id={part_id}")
    path = f"api/v1/components/{sanitize(part_id)}/enable"
    url = f"https://{config.rest_api}/{path}"

    resp = _patch(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------   

def patch_hwitem_status(part_id, data, **kwargs):
    #{{{
    """Enables/disables an HWItem

    Structure for "data":
        {
            "comments": <str>,
            "component": {
                "part_id": <str>
            },
            "status": {
                "id": <int>
            }
        }

    Structure of returned response:
        {
            "component_id": 150964,
            "data": "Created",
            "new_status": "available",
            "part_id": "Z00100300022-00064",
            "status": "OK"
        }

    Note: at the time of this writing, "comments" overwrites the comment for
    the item itself!
    """
    logger.debug(f"<patch_hwitem_enable> part_id={part_id}")
    path = f"api/v1/components/{sanitize(part_id)}/status"
    url = f"https://{config.rest_api}/{path}"

    resp = _patch(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------
 
def get_subcomponents(part_id, **kwargs):
    #{{{
    logger.debug(f"<get_subcomponents> part_id={part_id}")
    path = f"api/v1/components/{sanitize(part_id)}/subcomponents" 
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def patch_subcomponents(part_id, data, **kwargs):
    #{{{
    logger.debug(f"<patch_subcomponents> part_id={part_id}")
    path = f"api/v1/components/{sanitize(part_id)}/subcomponents" 
    url = f"https://{config.rest_api}/{path}"
    
    resp = _patch(url, data=data, **kwargs)
    return resp
    #}}}


#-----------------------------------------------------------------------------

def get_hwitem_locations(part_id, **kwargs):
    #{{{
    """Get a list of locations for a HWItem

    Structure of returned response:
        {
            "data": [
                {
                    "arrived": "2024-04-04T07:06:47.947419-05:00",
                    "comments": "arrived at U-Minn",
                    "created": "2024-04-04T07:06:54.107014-05:00",
                    "creator": "Alex Wagner",
                    "id": 2,
                    "link": {
                        "href": "/cdbdev/api/v1/locations/2",
                        "rel": "details"
                    },
                    "location": "University of Minnesota Twin Cities"
                }
            ],
            "link": {
                "href": "/cdbdev/api/v1/components/Z00100300022-00020/locations",
                "rel": "self"
            },
            "status": "OK"
        }    
    """
    logger.debug(f"<get_hwitem_locations> part_id={part_id}")
    path = f"api/v1/components/{sanitize(part_id)}/locations"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs) 
    return resp
    #}}}

#-----------------------------------------------------------------------------

def post_hwitem_location(part_id, data, **kwargs):
    #{{{
    """Add the current location for a HWItem

    Structure for "data":
        {
            "location": 
            {
                "id": <int>,
            },
            "arrived": <str: ISO 8601 datetime>,
            "comments": <str>
        }

    Structure of returned response:

        {
            "data": "Created",
            "id": 2,
            "status": "OK"
        }

    NOTE: "id" appears to be an oid internal to the HWDB and isn't 
    of any particular use when using the REST API.
    """
    
    logger.debug(f"<post_hwitem_location> part_id={part_id}")
    path = f"api/v1/components/{sanitize(part_id)}/locations"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _post(url, data, **kwargs) 
    return resp
    #}}}

##############################################################################
#
#  COMPONENT TYPES
#
##############################################################################

def get_component_type(part_type_id, **kwargs):
    #{{{
    """Get information about a specific component type

    Response Structure:
        {
            "data": {
                "category": "generic",
                "comments": null,
                "connectors": {},
                "created": "2023-09-21T10:26:08.572086-05:00",
                "creator": {
                    "id": 12624,
                    "name": "Hajime Muramatsu",
                    "username": "hajime3"
                },
                "full_name": "Z.Sandbox.HWDBUnitTest.jabberwock",
                "id": 1085,
                "manufacturers": [],
                "part_type_id": "Z00100300030",
                "properties": null,
                "roles": [],
                "subsystem": {
                    "id": 171,
                    "name": "HWDBUnitTest"
                }
            },
            "link": {...},
            "methods": [...],
            "status": "OK"
        }
    """

    logger.debug(f"<get_component_type> part_type_id={part_type_id}")
    path = f"api/v1/component-types/{sanitize(part_type_id)}"
    url = f"https://{config.rest_api}/{path}"
   
    resp = _get(url, **kwargs) 
    return resp
    #}}}

#-----------------------------------------------------------------------------

def patch_component_type(part_type_id, data, **kwargs):
    #{{{
    """Update properties for a component type

    Structure for "data":
        {
            "comments": "updating via REST API",
            "connectors": {},
            "manufacturers": [7, 50],
            "name": "jabberwock",
            "part_type_id": "Z00100300030",
            "properties":
            {
                "specifications":
                {
                    "datasheet":
                    {
                        "Flavor": None,
                        "Color": None,
                    },
                }
            },
            "roles": [4]
        }

    Response Structure:
        {
            "data": "Updated",
            "id": 1085,
            "part_type_id": "Z00100300030",
            "status": "OK"
        }

    """

    logger.debug(f"<patch_component_type> part_type_id={part_type_id} "
                "data={data}")
    path = f"api/v1/component-types/{sanitize(part_type_id)}"
    url = f"https://{config.rest_api}/{path}"

    resp = _patch(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_component_type_connectors(part_type_id, **kwargs):
    #{{{
    logger.debug(f"<get_component_type_connectors> part_type_id={part_type_id}")
    path = f"api/v1/component-types/{sanitize(part_type_id)}/connectors"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs) 
    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_component_type_specifications(part_type_id, **kwargs):
    #{{{
    logger.debug(f"<get_component_type_specifications> part_type_id={part_type_id}")
    path = f"api/v1/component-types/{sanitize(part_type_id)}/specifications"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs) 
    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_component_types(project_id, system_id, subsystem_id=None, *,
                        full_name=None, comments=None,
                        #part_type_id=None,
                        page=None, size=None, fields=None, **kwargs):
    #{{{
    logger.debug(f"<get_component_types> project_id={project_id}, "
                    f"system_id={system_id}, subsystem_id={subsystem_id}")
    
    # There are actually two different REST API methods for this, one that
    # takes proj/sys/subsys and the other that takes only proj/sys. You 
    # can use a wildcard "0" for subsys for the first one and get the same
    # results as the second, so there really was no need. But, we'll go ahead
    # and use both, switching based on if subsystem_id is or isn't None.
    if subsystem_id is None:
        path = (f"api/v1/component-types/{sanitize(project_id)}/"
                f"{sanitize(system_id)}")
    else:
        path = (f"api/v1/component-types/{sanitize(project_id)}/"
                f"{sanitize(system_id)}/{sanitize(subsystem_id)}")
    url = f"https://{config.rest_api}/{path}"
    
    params = []
    if page is not None:
        params.append(("page", page))
    if size is not None:
        params.append(("size", size))
    if full_name is not None:
        params.append(("full_name", full_name))
    if comments is not None:
        params.append(("comments", comments))
    if fields is not None:
        params.append(("fields", ",".join(fields)))

    resp = _get(url, params=params, **kwargs) 
    return resp
    #}}}

#-----------------------------------------------------------------------------

def patch_hwitem_subcomp(part_id, data, **kwargs):
    #{{{
    logger.debug(f"<patch_hwitem_subcomp> part_id={part_id}")
    path = f"api/v1/components/{sanitize(part_id)}/subcomponents" 
    url = f"https://{config.rest_api}/{path}" 
    
    resp = _patch(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def post_hwitems_bulk(part_type_id, data, **kwargs):
    #{{{
    logger.debug(f"<post_hwitems_bulk> type_id={part_type_id}")
    path = f"api/v1/component-types/{sanitize(part_type_id)}/bulk-add" 
    url = f"https://{config.rest_api}/{path}" 
    
    resp = _post(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def patch_hwitems_bulk(part_type_id, data, **kwargs):
    #{{{
    logger.debug(f"<patch_hwitems_bulk> type_id={part_type_id}")
    path = f"api/v1/component-types/{sanitize(part_type_id)}/bulk-update" 
    url = f"https://{config.rest_api}/{path}" 
    
    resp = _patch(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def patch_hwitems_enable_bulk(data, **kwargs):
    #{{{
    logger.debug(f"<patch_hwitems_enable_bulk>")
    path = f"api/v1/components/bulk-enable" 
    url = f"https://{config.rest_api}/{path}" 
    
    resp = _patch(url, data=data, **kwargs)
    return resp
    #}}}

##############################################################################
#
#  TESTS
#
##############################################################################

def get_test_types(part_type_id, **kwargs):
    #{{{
    """Get a list of test types for a given part type

    Implements /api/v1/component-types/{part-type-id}/test-types
    
    The list returned only contains summary information about each
    test types. Use "get_test_type" to get details, including the
    specification.
    """

    logger.debug(f"<get_test_types> part_type_id={part_type_id}")
    path = f"api/v1/component-types/{part_type_id}/test-types"
    url = f"https://{config.rest_api}/{path}"

    resp = _get(url, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_test_type(part_type_id, test_type_id, **kwargs):
    #{{{
    """Get information about a specific test type for a given part type id

    Implements /api/v1/component-types/{part_type_id}/test-types/{test_type_id}

    Use "get_test_types" to obtain the test_type_id needed for this
    function.

    If history is True, the entire specification history is returned, instead
    of just the most recent entry.
    """

    logger.debug(f"<get_test_type> part_type_id={part_type_id}, "
                f"test_type_id={test_type_id}")
    path = f"api/v1/component-types/{part_type_id}/test-types/{test_type_id}"
    url = f"https://{config.rest_api}/{path}"

    resp = _get(url, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_test_type_by_oid(oid, **kwargs):
    #{{{
    """Get a test type with a given oid

    Implements /api/v1/component-test-types/{oid}

    This function is provided for completeness, but there's no consistent way
    to obtain the oid to use here.
    """

    logger.debug(f"<get_test_type_by_oid> oid={oid}")
    path = f"api/v1/component-test-types/{oid}"
    url = f"https://{config.rest_api}/{path}"

    resp = _get(url, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_hwitem_tests(part_id, history=False, **kwargs):
    #{{{
    """Get a list of tests for a given part_id

    Implements /api/v1/components/{part_id}/tests

    Returns the last instance of each test type for the given part_id.
    Only test types that have actual tests will be shown in the list. To get
    available test types, use get_test_types.

    If history is True, all instances of all test types will be returned,
    instead of the most recent.
    """

    logger.debug(f"<get_hwitem_tests> part_id={part_id}")
    path = f"api/v1/components/{part_id}/tests"
    url = f"https://{config.rest_api}/{path}"

    params = [("history", str(history).lower())]
    
    resp = _get(url, params=params, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_hwitem_test(part_id, test_type_id, history=False, **kwargs):
    #{{{
    """Get a list of tests for a given part_id and test_type_id

    Implements /api/v1/components/{part_id}/tests/{test_type_id}

    Returns only the last instance of the test_type_id for the given part_id,
    unless history is True.

    This appears to be the only way to get the images for a test.
    """

    logger.debug(f"<get_hwitem_test> part_id={part_id}, test_type_id={test_type_id}")
    path = f"api/v1/components/{part_id}/tests/{test_type_id}"
    url = f"https://{config.rest_api}/{path}"

    params = [("history", str(history).lower())]
    
    resp = _get(url, params=params, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def post_test_type(part_type_id, data, **kwargs):
    #{{{
    """Create a new test type for a component type

    Structure for 'data':
        {
            "comments": <str>,
            "component_type": {"part_type_id": <str>},
            "name": <str>,
            "specifications": <dict>
        }

    Structure for returned response:
        {
            'data': 'Created', 
            'name': <str>, 
            'status': 'OK', 
            'test_type_id': <int>}
        }
    """


    logger.debug(f"<post_test_types> part_type_id={part_type_id}")
    path = f"api/v1/component-types/{part_type_id}/test-types"
    url = f"https://{config.rest_api}/{path}"

    resp = _post(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def patch_test_type(part_type_id, data, **kwargs):
    #{{{
    """Update a test type for a component type

    NOTE: THIS DOES NOT WORK BECAUSE THERE'S NO API ENDPOINT FOR PATCHING TESTS


    Structure for 'data':
        {
            "comments": <str>,
            "component_type": {"part_type_id": <str>},
            "name": <str>,
            "specifications": <dict>
        }

    Structure for returned response:
        {
            'data': 'Created', 
            'name': <str>, 
            'status': 'OK', 
            'test_type_id': <int>}
        }
    """


    logger.debug(f"<patch_test_types> part_type_id={part_type_id}")
    path = f"api/v1/component-types/{part_type_id}/test-types"
    url = f"https://{config.rest_api}/{path}"

    resp = _patch(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def post_test(part_id, data, **kwargs):
    #{{{
    '''Post a new test

    Structure for data:    
        {
          "comments": "string",
          "test_data": {},
          "test_type": "string"
        }

    Response structure:
        {
            "data": "Created",
            "status": "OK",
            "test_id": 14464,
            "test_type_id": 563
        }
    '''
    logger.debug(f"<post_test> part_id={part_id}")
    path = f"api/v1/components/{part_id}/tests"
    url = f"https://{config.rest_api}/{path}"

    resp = _post(url, data=data, **kwargs)
    return resp
    #}}}

##############################################################################
#
#  MISCELLANEOUS
#
##############################################################################

def whoami(**kwargs):
    #{{{
    """Gets information about the current user

    Return structure:
        {
            "data": {
                "active": <bool>,
                "administrator": <bool>,
                "affiliation": <str>,
                "architect": <bool>,
                "email": <str>,
                "full_name": <str>,
                "roles": [
                    {
                        "id": <int>,
                        "name": <str>
                    },
                    ...
                ],
                "user_id": <int>,
                "username": <str>
            },
            "link": {...},
            "status": "OK"
        }
    """

    logger.debug(f"<whoami>")
    path = "api/v1/users/whoami"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_countries(**kwargs):
    #{{{
    logger.debug(f"<get_countries>")
    path = "api/v1/countries"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_institutions(**kwargs):
    #{{{
    logger.debug(f"<get_institutions>")
    path = "api/v1/institutions"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_manufacturers(**kwargs):
    #{{{
    logger.debug(f"<get_manufacturers>")
    path = "api/v1/manufacturers"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_projects(**kwargs):
    #{{{
    logger.debug(f"<get_projects>")
    path = "api/v1/projects"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_roles(**kwargs):
    #{{{
    logger.debug(f"<get_roles>")
    path = "api/v1/roles"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_users(**kwargs):
    #{{{
    logger.debug(f"<get_users>")
    path = "api/v1/users"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_user(user_id, **kwargs):
    #{{{
    logger.debug(f"<get_user> user_id={user_id}")
    path = f"api/v1/users/{user_id}"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_role(role_id, **kwargs):
    #{{{
    logger.debug(f"<get_role> role_id={role_id}")
    path = f"api/v1/roles/{role_id}"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_subsystems(project_id, system_id, **kwargs):
    #{{{
    logger.debug(f"<get_subsystems> project_id={project_id}, system_id={system_id}")
    path = f"api/v1/subsystems/{project_id}/{system_id}"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_subsystem(project_id, system_id, subsystem_id, **kwargs): 
    #{{{
    logger.debug(f"<get_subsystem> project_id={project_id}, "
                    "system_id={system_id}, subsystem_id={subsystem_id}")
    path = f"api/v1/subsystems/{project_id}/{system_id}/{subsystem_id}"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_systems(project_id, **kwargs):
    #{{{
    logger.debug(f"<get_systems> project_id={project_id}")
    path = f"api/v1/systems/{project_id}"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_system(project_id, system_id, **kwargs):
    #{{{
    logger.debug(f"<get_system> project_id={project_id}, system_id={system_id}")
    path = f"api/v1/systems/{project_id}/{system_id}"
    url = f"https://{config.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

##############################################################################

if __name__ == "__main__":
    pass
