#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/RestApiV1/exceptions.py
Copyright (c) 2024 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

LOG_ON_CREATION = False

if LOG_ON_CREATION:
    from Sisyphus.Configuration import config
    logger = config.getLogger(__name__)


class RestApiException(Exception):
    def __init__(self, *args, **kwargs):
        if LOG_ON_CREATION:
            msg = [f"'{type(self).__name__}' exception was created."]
            if len(args) > 0:
                msg.append(f"args: {args}")
            if len(kwargs) > 0:
                msg.append(f"kwargs: {kwargs}")
            msg.append("This message is a courtesy in case the code that "
                    "triggered this exception does not catch and log it. "
                    "Note that the exception log entry (if present) may appear "
                    "before this message.")
            logger.warning(" ".join(msg))
        super().__init__(*args, **kwargs)

    """Base class for RestApi exceptions."""
    pass

class MissingArguments(RestApiException):
    """The function or method expected one or more parameters that were 
    not present.

    Example use case: a function expected an ID or a name, but
    received neither one.
    """

class IncompatibleArguments(RestApiException):
    """The arguments supplied were not compatible with each other

    Example use case: A function might allow a Part Type ID or a 
    Part Type Name, but permit being given both, as long as they
    resolve to the same Component Type. If they do not, raise this
    exception.
    """

class AmbiguousParameters(RestApiException):
    """The arguments supplied did not uniquely identify a resource

    Example use cases: 
      * attempting to look up an institution or
        manufacturer with a string containing a wildcard, and receiving
        more than one result, in a context where the institution or
        manufacturer was expected to be unique
      * trying to identify an item by serial number (and part type), but
        there is more than one item using that serial number
    """

class NoSessionAvailable(RestApiException):
    """The "session" object was not properly initialized

    This typically means that there's something wrong with the current
    configuration.
    """

class ServerError(RestApiException):
    """The REST API server returned an error"""

class InvalidResponse(RestApiException):
    """The REST API server returned invalid data

    The data returned by the server was not a valid format.
    Usually, the response is expected to be a JSON dictionary. If it
    returns something else, use this exception.
    """

class ExpiredSignature(RestApiException):
    """The REST API server returned 'ExpiredSignatureError'

    This is for the new verification system implemented in March 2025
    """

class CertificateError(RestApiException):
    """The REST API server complained about the certificate

    At the time of this writing, a bad certificate (possibly expired)
    will cause the REST API to return a 400 code and the response
    will be in HTML instead of JSON. But the response can be searched
    for 'The SSL certificate error', at which time, this exception
    should be raised.
    """

class InsufficientPermissions(RestApiException):
    """The user does not have the authority for this request"""

class DatabaseError(RestApiException):
    """The REST API server returned an "ERROR" status

    If a more specific reason can be determined for causing the error,
    it is better to create a subclass of this class and return it
    instead.
    """

class BadSpecificationFormat(DatabaseError):
    """The Specification or Test Result data did not match the definition."""

class BadDataFormat(DatabaseError):
    """The data being submitted via POST/PATCH was rejected by the server

    Typically, this means there are missing or extra fields.
    """


class NameResolutionFailure(RestApiException):
    """The URL of the server could not be resolved"""

class ConnectionFailed(RestApiException):
    """The REST API server could not be reached"""
    
class NotFound(RestApiException):
    """The function or method did not get a result"""
    
class MaxRecordsExceeded(RestApiException):
    """The query returned more records than is permitted in this context"""


