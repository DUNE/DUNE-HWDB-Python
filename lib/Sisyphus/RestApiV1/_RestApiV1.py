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

from .RestApiSession import SessionManager

from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus.Utils.Terminal.BoxDraw import MessageBox
import sys

import Sisyphus.Configuration as cfg # for keywords
from .exceptions import *
from .keywords import *

from copy import copy, deepcopy
import json
import requests
import urllib.parse
import functools
import threading
import time
import subprocess
import os
from contextlib import nullcontext

###############################################################################
#
#  REQUESTS 2.32 HACKS
#  -------------------
#
#  We discovered that the Requests 2.32 library had a bug where if certificates
#  were being used, and the library was being used in multiple threads, the
#  application using it would often suffer a segmentation fault.
#
#  You can check which version of requests you are using by using this command:
#
#      pip list | grep requests
# 
#  It was also discovered that if requests were made with {'verify': False} in
#  the headers, this problem would go away.
# 
#  This has become much less relevant now that we're using htgettoken to obtain
#  a bearer token that now must be sent in the header instead of using
#  certificates. Nevertheless, lest we need to revert to certificates and the
#  problem should return, we are retaining some precautionary measures.
#
#  (1) The Configuration module will insert {'verify': True} into its default
#      profiles, which the user can change to False if the need arises. (They
#      will have to edit the config file manually to do so.) 
#
#  (2) If {'verify': False} is used, the application will constantly spit out
#      some really annoying warnings. So we will disable them:
#
import warnings
import urllib3
warnings.filterwarnings("ignore", 
                    category=urllib3.exceptions.InsecureRequestWarning)
#
#  (3) Another way to keep multiple threads from making requests at the same
#      time is to use a threading.Lock() object to allow only one thread at a
#      time into the block of code making the request.
# 
#      A configuration setting called "throttle_lock" is available to switch
#      this on or off. By default this is off. A context manager is used to
#      to do the locking:
#
if config.active_profile.settings.get(cfg.KW_THROTTLE_LOCK, False):
    throttle_lock = threading.Lock()
else:
    throttle_lock = nullcontext()
#
###############################################################################

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
def get_session(use_config=None):

    if use_config is None:
        use_config = config

    if not hasattr(thread_local, 'config'):
        thread_local.config = use_config
        new_session = True
    else:
        if thread_local.config == use_config:
            new_session = False
        else:
            thread_local.config = use_config
            new_session = True

# This is just to keep multiple lines of log messages together, so they
# won't get separated if two threads are trying to log a the same time.
log_lock = threading.Lock()



# To help with logging
def func_name():
    '''get the name of the function calling this function'''
    return sys._getframe(1).f_code.co_name

#-----------------------------------------------------------------------------

class retry:
    #{{{
    '''Wrapper for RestApi functions to permit them to retry on a connection failure'''

    def __init__(self, timeouts=None ):
        # timeouts should be a list containing the timeout to use on each try
        # when executing a request. The total number of retries allowed will be
        # the length of this list. To not specify a timeout (and thus use
        # whatever the default is for the library... maybe 300 seconds?) use
        # None.
        #
        # Examples:
        #     None: equivalent to [None]
        #     [None]: do only 1 attempt, use the library's default timeout
        #     30: equivalent to [30]
        #     [30]: do only 1 attempt, with a timeout of 30 seconds
        #     [5, 10, None]: do one attempt with a 5 second timeout, a second
        #                    attempt with a 10 second timeout, and a third
        #                    attempt using the library's default timeout.
        #
        # Note that this is to set the default timeouts the wrapped function
        # will use, but the function itself can also take a timeouts parameter
        # to override these defaults. Additionally, the config profile can
        # also set these.
        #
        # The order of precedence is that what is sent to the function will
        # override the config profile settings, and the config profile settings
        # will override the defaults set here.

        if type(timeouts) not in (list, tuple):
            self.default_timeouts = (timeouts,)
        else:
            self.default_timeouts = tuple(timeouts)

    def __call__(self, function):

        @functools.wraps(function)
        def wrapped_function(*args, **kwargs):

            status_callback = kwargs.pop("status_callback", None)

            if status_callback is not None:
                update_status = lambda msg: status_callback(msg)
            else:
                update_status = lambda msg: None

            profile = kwargs.get("profile", config.active_profile)

            # Use the 'timeouts' passed to the function, or from the 
            # config settings, or the defaults, in that order. (I.e., use
            # the first one that isn't None)

            timeouts = ( kwargs.pop("timeouts", None)
                        or profile.settings.get(cfg.KW_TIMEOUTS, None)
                        or self.default_timeouts )

            last_err = None
            logger.debug(f"RestApi operation will be tried {len(timeouts)} times.")
            for try_num, timeout in enumerate(timeouts):
                try:
                    if type(last_err) in (ExpiredSignature, CurrentlyUnavailable):
                        SessionManager(profile).profile_manager.refresh()                        

                except Exception as exc:
                    logger.error(f"Failed to refresh token: {exc}")

                try:
                    if timeout is not None:
                        kwargs['timeout'] = timeout
                    # Note that someone could pass 'timeout' in the kwargs
                    # instead of our 'timeouts' parameter. This is a valid
                    # parameter, so just leave it there.

                    # Display a message in the terminal, but only if we're on 
                    # the main thread. This message will be erased when the 
                    # call is finished. It has to be on the main thread because
                    # the result could be unpredictable if we allow multiple
                    # threads to write and erase messages
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

                    # Newer messaging scheme for GUI applications: send an
                    # update to a callback function. 
                    # TODO: Implement a callback that writes to the terminal
                    # and eliminate the previous section of code
                    s = ("[sending data]" if try_num == 0
                            else f"[sending data (attempt #{try_num+1})]")
                    update_status(s)

                    resp = function(*args, **kwargs)

                    update_status("[finished]")


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
                except CurrentlyUnavailable as err:
                    msg = (f"Server claims this is currently unavailable in {function.__name__} "
                            f"in thread '{threading.current_thread().name}' "
                            f"(attempt #{try_num+1})")
                    logger.warning(msg)
                    time.sleep(5)
                    last_err = err
                except Exception as exc:
                    # If we don't recognize the exception, assume that there
                    # was actually somthing wrong with the request itself and
                    # not something that trying again would fix. Re-raise
                    # the exception.
                    msg = (f"Exception: {exc!r} while calling {function.__name__} "
                            f"in thread '{threading.current_thread().name}' "
                            f"(attempt #{try_num+1})")
                    logger.error(msg)
                    last_err = exc
                    raise


                finally:
                    # Clean up the message that was displayed in the terminal
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

DEFAULT_TIMEOUTS = (5, 10, 15, 30, 60)

@retry(timeouts=DEFAULT_TIMEOUTS)
def _request(method, url, *args, return_type="json", **kwargs):
    #{{{
    '''Does a session.request() with some extra error handling

    "Master" function for all gets, posts, and patches. If the return
    type is "json" (which is the default), it will enforce that the 
    response is a valid JSON dictionary that contains a "status" of 
    "OK" otherwise.
    '''

    profile = kwargs.pop('profile', None) or config.active_profile

    session_manager = SessionManager(profile)

    threadname = threading.current_thread().name
    msg = (f"<_request> [{method.upper()}] "
            f"url='{url}' method='{method.lower()}'")
    logger.debug(msg) 

    if profile.settings.get(cfg.KW_LOG_REQUEST_JSON, False) and "json" in kwargs:
        try:
            msg = f"json =\n{json.dumps(kwargs['json'], indent=4)}"
        except json.JSONDecodeError as exc:
            msg = f"data =\n{kwargs['json']}"
        logger.debug(msg)

    augmented_kwargs = {**profile.settings.get(cfg.KW_EXTRA_KWARGS, {}), **kwargs}
        
    extra_info = \
    [
        "Additional Information:",
        f"| thread: {threadname}",
        f"| url: {url}",
        f"| method: {method}",
        f"| args: {args}, kwargs: {augmented_kwargs}",
    ]
    
    log_headers = augmented_kwargs.pop("log_headers", False)

    # Pop this, but don't do anything with it. "retry" handles it.
    status_callback = augmented_kwargs.pop("status_callback", None)    

    # Pop this, but don't do anything with it. It's for signaling further
    # up the chain whether or not to look in the cache for this. But, at
    # this point, it has already been decided to actually do the request.
    refresh = augmented_kwargs.pop("refresh", None)    
    
    try:
        if profile.settings.get(cfg.KW_LOG_HEADERS, False):
            session = session_manager.session

            # We need to pop some of the augmented_kwargs because Request 
            # doesn't accept them. We will have to re-attach them to the 'send'
            send_kwargs = {
                k:v for k, v in [
                    ('verify', augmented_kwargs.pop('verify', None)),
                    ('timeout', augmented_kwargs.pop('timeout', None)) ]
                if v is not None
            }

            req = requests.Request(method, url, *args, **augmented_kwargs)
            prepped = session.prepare_request(req)

            with log_lock:
                logger.info(f"prepped.headers: {prepped.headers}")
                if prepped.body is not None and len(prepped.body) > 1000:
                    logger.info(f"prepped.body (beginning): {prepped.body[:800]}")
                    logger.info(f"prepped.body (end): {prepped.body[-200:]}")
                else:
                    logger.info(f"prepped.body: {prepped.body}")


            with throttle_lock:
                resp = session_manager.session.send(prepped, **send_kwargs)

        else:
            with throttle_lock:
                resp = session_manager.session.request(method, url, *args, **augmented_kwargs)


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
        raise

    #extra_info.append(f"| request headers: {resp.request.headers}")
    extra_info.append(f"| status code: {resp.status_code}")
    extra_info.append(f"| elapsed: {resp.elapsed}")
    if log_headers:
        extra_info.append(f"| response headers: {resp.headers}")
    if resp.encoding == "utf-8":
        extra_info.append(f"| response: {resp.text}")
    else:
        extra_info.append(f"| response: [binary] {resp.text}")

    database_errors = [
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

    # At this point, we don't know if the response is valid JSON, normal
    # text, or binary data, but we'll scan it as if it's text and look
    # for the kinds of errors that the REST API spits out (as HTML)
    if KW_DATA in resp.text:
        for database_error in database_errors:
            if (database_error["signature"] in resp.text):
                msg = database_error["message"]
                exc_type = database_error["exc_type"]
                with log_lock:
                    logger.error(msg)
                    extra_info.append(f"| exc_type: {exc_type.__name__}")
                    logger.info('\n'.join(extra_info))
                raise exc_type(msg)


    if return_type.lower() == "json":
        #{{{
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
            if "currently unavailable" in resp.text:
                msg = "The certificate was not accepted by the server."
                with log_lock:
                    exc_type = CurrentlyUnavailable
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
        #}}}
    else:
        # The data isn't supposed to be JSON, so there's not much we can
        # do to validate it further.
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

    logger.debug(f"<{func_name()}>")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/{sanitize(part_id)}/images"
    url = f"https://{profile.rest_api}/{path}"

    resp = _get(url, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def post_hwitem_image(part_id, data, filename, **kwargs):
    #{{{
    """Add an image for an Item

    To add a comment, you need to put it in 'data', e.g.,
    data = {
        "comments": "this is my comment"
    }
    """
    
    logger.debug(f"<{func_name()}> part_id={part_id}, filename={filename}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/{sanitize(part_id)}/images"
    url = f"https://{profile.rest_api}/{path}"

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
    logger.debug(f"<{func_name()}>")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/component-types/{sanitize(part_type_id)}/images"
    url = f"https://{profile.rest_api}/{path}"
    
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
    logger.debug(f"<{func_name()}> part_id={part_id}, test_id={test_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/{sanitize(part_id)}/tests/{sanitize(test_type_id)}/images"
    url = f"https://{profile.rest_api}/{path}"
    
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
    logger.debug(f"<{func_name()}>")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/img/{image_id}"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, return_type="raw", **kwargs)

    if write_to_file is not None:
        with open(write_to_file, "wb") as fp:
            fp.write(resp.content)

    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_hwitem_qrcode(part_id, write_to_file=None, **kwargs):
    #{{{
    logger.debug(f"<{func_name()}> part_id={part_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/get-qrcode/{sanitize(part_id)}"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, return_type="raw", **kwargs)
    
    if write_to_file is not None:
        with open(write_to_file, "wb") as fp:
            fp.write(resp.content)

    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_hwitem_barcode(part_id, write_to_file=None, **kwargs):
    #{{{
    logger.debug(f"<{func_name()}> part_id={part_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/get-barcode/{sanitize(part_id)}"
    url = f"https://{profile.rest_api}/{path}"
    
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

    logger.debug(f"<{func_name()}> part_id={part_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/{sanitize(part_id)}"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs) 
    return resp
    #}}}

#-----------------------------------------------------------------------------

#def get_hwitems(part_type_id, *,
#                page=None, size=None, fields=None, serial_number=None, part_id=None, **kwargs):
def get_hwitems(part_type_id, *,
                page=None, size=None, fields=None, serial_number=None, part_id=None, comments=None,
                manufacturer=None,creator=None,country_of_origin=None,resp_institution=None,
                status=None,location=None,certified_qaqc=None,qaqc_uploaded=None,is_installed=None,**kwargs):
    #{{{
    logger.debug(f"<{func_name()}> part_type_id={part_type_id},"
                f"page={page}, size={size}, fields={fields}, "
                f"serial_number={serial_number}, part_id={part_id}, comments={comments},"
                f"manufacturer={manufacturer}, creator={creator},"
                f"country_of_origin={country_of_origin}, resp_institution={resp_institution},"
                f"status={status}, location={location}, certified_qaqc={certified_qaqc},"
                f"qaqc_uploaded={qaqc_uploaded}, is_installed={is_installed}")
    
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/component-types/{sanitize(part_type_id)}/components"
    url = f"https://{profile.rest_api}/{path}"

    params = []
    if page is not None:
        params.append(("page", page))
    if size is not None:
        params.append(("size", size))
    if serial_number is not None:
        params.append(("serial_number", serial_number))
    if part_id is not None:
        params.append(("part_id", part_id))
    if comments is not None:
        params.append(("comments", comments))
    ## *** currently broken in REST API
    if fields is not None:
        params.append(("fields", ",".join(fields)))

    if manufacturer is not None:
        params.append(("manufacturer", manufacturer))
    if creator is not None:
        params.append(("creator", creator))
    if country_of_origin is not None:
        params.append(("country_of_origin", country_of_origin))
    if resp_institution is not None:
        params.append(("resp_institution", resp_institution))
    if status is not None:
        params.append(("status", status))
    if location is not None:
        params.append(("location", location))
    if certified_qaqc is not None:
        params.append(("certified_qaqc", certified_qaqc))
    if qaqc_uploaded is not None:
        params.append(("qaqc_uploaded", qaqc_uploaded))
    if is_installed is not None:
        params.append(("is_installed", is_installed))

        
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

    logger.debug(f"<{func_name()}> part_type_id={part_type_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/component-types/{sanitize(part_type_id)}/components" 
    url = f"https://{profile.rest_api}/{path}" 
    
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
            "status": {"id": <status_id>},
            "specifications": {...},
        }

    (True as of 2025-04-21, but is subject to change!!)
    status_id:
        'available' = 1
        'not available' = 2
        'permanently not available' = 3

    Structure of returned response:
        {
            "component_id": 44757,
            "data": "Created",
            "id": 151635,
            "part_id": "Z00100300001-00001",
            "status": "OK"
        }
    """

    logger.debug(f"<{func_name()}> part_id={part_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/{sanitize(part_id)}" 
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _patch(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def post_bulk_hwitems(part_type_id, data, **kwargs):
    #{{{
    logger.debug(f"<{func_name()}> part_type_id={part_type_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/component-types/{sanitize(part_type_id)}/bulk-add"
    url = f"https://{profile.rest_api}/{path}"
                
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
    logger.debug(f"<{func_name()}> part_id={part_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/{sanitize(part_id)}/enable"
    url = f"https://{profile.rest_api}/{path}"

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
    logger.debug(f"<{func_name()}> part_id={part_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/{sanitize(part_id)}/status"
    url = f"https://{profile.rest_api}/{path}"

    resp = _patch(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------
 
def get_subcomponents(part_id, **kwargs):
    #{{{
    logger.debug(f"<{func_name()}> part_id={part_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/{sanitize(part_id)}/subcomponents" 
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def patch_subcomponents(part_id, data, **kwargs):
    #{{{
    '''Attach subcomponents to a component

    Structure for "data":
        {
            "component":
            {
                "part_id": <part_id>,
            },
            "subcomponents":
            {
                <func pos name>: <part_id>,
                <func pos name>: <part_id>,
                <func pos name>: <part_id>
            }
        }

    Structure of returned response:
        {
            "component_id": 181869,
            "data": "Updated",
            "part_id": "D00599800007-00087",
            "status": "OK"
        }

    '''

    logger.debug(f"<{func_name()}> part_id={part_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/{sanitize(part_id)}/subcomponents" 
    url = f"https://{profile.rest_api}/{path}"
    
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
    logger.debug(f"<{func_name()}> part_id={part_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/{sanitize(part_id)}/locations"
    url = f"https://{profile.rest_api}/{path}"
    
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

    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/{sanitize(part_id)}/locations"
    url = f"https://{profile.rest_api}/{path}"
    
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

    logger.debug(f"<{func_name()}> part_type_id={part_type_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/component-types/{sanitize(part_type_id)}"
    url = f"https://{profile.rest_api}/{path}"
   
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

    logger.debug(f"<{func_name()}> part_type_id={part_type_id} "
                "data={data}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/component-types/{sanitize(part_type_id)}"
    url = f"https://{profile.rest_api}/{path}"

    resp = _patch(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_component_type_connectors(part_type_id, **kwargs):
    #{{{
    logger.debug(f"<{func_name()}> part_type_id={part_type_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/component-types/{sanitize(part_type_id)}/connectors"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs) 
    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_component_type_specifications(part_type_id, **kwargs):
    #{{{
    logger.debug(f"<{func_name()}> part_type_id={part_type_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/component-types/{sanitize(part_type_id)}/specifications"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs) 
    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_component_types(project_id, system_id, subsystem_id=None, *,
                        full_name=None, comments=None,
                        #part_type_id=None,
                        page=None, size=None, fields=None, **kwargs):
    #{{{
    logger.debug(f"<{func_name()}> project_id={project_id}, "
                    f"system_id={system_id}, subsystem_id={subsystem_id}")
    profile = kwargs.get('profile', config.active_profile)
    
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
    url = f"https://{profile.rest_api}/{path}"
    
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
    logger.debug(f"<{func_name()}> part_id={part_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/{sanitize(part_id)}/subcomponents" 
    url = f"https://{profile.rest_api}/{path}" 
    
    resp = _patch(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def post_hwitems_bulk(part_type_id, data, **kwargs):
    #{{{
    logger.debug(f"<{func_name()}> part_type_id={part_type_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/component-types/{sanitize(part_type_id)}/bulk-add" 
    url = f"https://{profile.rest_api}/{path}" 
    
    resp = _post(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def patch_hwitems_bulk(part_type_id, data, **kwargs):
    #{{{
    logger.debug(f"<{func_name()}> type_id={part_type_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/component-types/{sanitize(part_type_id)}/bulk-update" 
    url = f"https://{profile.rest_api}/{path}" 
    
    resp = _patch(url, data=data, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def patch_hwitems_enable_bulk(data, **kwargs):
    #{{{
    logger.debug(f"<{func_name()}>")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/bulk-enable" 
    url = f"https://{profile.rest_api}/{path}" 
    
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

    logger.debug(f"<{func_name()}> part_type_id={part_type_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/component-types/{sanitize(part_type_id)}/test-types"
    url = f"https://{profile.rest_api}/{path}"

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

    logger.debug(f"<{func_name()}> part_type_id={part_type_id}, "
                f"test_type_id={test_type_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/component-types/{sanitize(part_type_id)}/test-types/{sanitize(test_type_id)}"
    url = f"https://{profile.rest_api}/{path}"

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

    logger.debug(f"<{func_name()}> oid={oid}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/component-test-types/{sanitize(oid)}"
    url = f"https://{profile.rest_api}/{path}"

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

    logger.debug(f"<{func_name()}> part_id={part_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/{sanitize(part_id)}/tests"
    url = f"https://{profile.rest_api}/{path}"

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

    logger.debug(f"<{func_name()}> part_id={part_id}, test_type_id={test_type_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/{sanitize(part_id)}/tests/{sanitize(test_type_id)}"
    url = f"https://{profile.rest_api}/{path}"

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

    logger.debug(f"<{func_name()}> part_type_id={part_type_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/component-types/{sanitize(part_type_id)}/test-types"
    url = f"https://{profile.rest_api}/{path}"

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


    logger.debug(f"<{func_name()}> part_type_id={part_type_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/component-types/{sanitize(part_type_id)}/test-types"
    url = f"https://{profile.rest_api}/{path}"

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
    logger.debug(f"<{func_name()}> part_id={part_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/components/{part_id}/tests"
    url = f"https://{profile.rest_api}/{path}"

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

    logger.debug(f"<{func_name()}>")
    profile = kwargs.get('profile', config.active_profile)
    path = "api/v1/users/whoami"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_countries(**kwargs):
    #{{{
    logger.debug(f"<{func_name()}>")
    profile = kwargs.get('profile', config.active_profile)
    path = "api/v1/countries"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_institutions(**kwargs):
    #{{{
    logger.debug(f"<{func_name()}>")
    profile = kwargs.get('profile', config.active_profile)
    path = "api/v1/institutions"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_manufacturers(**kwargs):
    #{{{
    logger.debug(f"<{func_name()}>")
    profile = kwargs.get('profile', config.active_profile)
    path = "api/v1/manufacturers"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_projects(**kwargs):
    #{{{
    logger.debug(f"<{func_name()}>")
    profile = kwargs.get('profile', config.active_profile)
    path = "api/v1/projects"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_roles(**kwargs):
    #{{{
    logger.debug(f"<{func_name()}>")
    profile = kwargs.get('profile', config.active_profile)
    path = "api/v1/roles"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_users(**kwargs):
    #{{{
    logger.debug(f"<{func_name()}>")
    profile = kwargs.get('profile', config.active_profile)
    path = "api/v1/users"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_user(user_id, **kwargs):
    #{{{
    logger.debug(f"<{func_name()}> user_id={user_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/users/{sanitize(user_id)}"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_role(role_id, **kwargs):
    #{{{
    logger.debug(f"<{func_name()}> role_id={role_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/roles/{sanitize(role_id)}"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_subsystems(project_id, system_id, **kwargs):
    #{{{
    logger.debug(f"<{func_name()}> project_id={project_id}, system_id={system_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/subsystems/{sanitize(project_id)}/{sanitize(system_id)}"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_subsystem(project_id, system_id, subsystem_id, **kwargs): 
    #{{{
    logger.debug(f"<{func_name()}> project_id={project_id}, "
                    "system_id={system_id}, subsystem_id={subsystem_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/subsystems/{sanitize(project_id)}/{sanitize(system_id)}/{sanitize(subsystem_id)}"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp
    #}}}

#-----------------------------------------------------------------------------

def get_systems(project_id, **kwargs):
    #{{{
    logger.debug(f"<{func_name()}> project_id={project_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/systems/{sanitize(project_id)}"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

#-----------------------------------------------------------------------------

def get_system(project_id, system_id, **kwargs):
    #{{{
    logger.debug(f"<{func_name()}> project_id={project_id}, system_id={system_id}")
    profile = kwargs.get('profile', config.active_profile)
    path = f"api/v1/systems/{sanitize(project_id)}/{sanitize(system_id)}"
    url = f"https://{profile.rest_api}/{path}"
    
    resp = _get(url, **kwargs)
    return resp 
    #}}}

##############################################################################

if __name__ == "__main__":
    pass
