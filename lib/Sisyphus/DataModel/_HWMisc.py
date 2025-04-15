#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/DataModel/_HWMisc.py
Copyright (c) 2024 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

import Sisyphus.RestApiV1 as ra
import Sisyphus.RestApiV1.Utilities as ut

from copy import deepcopy
import json

class Country:
    #{{{
    def __init__(self, code=None, name=None, combo=None):
        """Lookup a country from the info provided

        * Needs at least one of country, name, or combo. A match must satisfy
            all criteria provided, so if both code and name are supplied,
            the country with that code must have that name.
        * Combo is a string that contains both code and name, e.g.,
            "(US) United States"
        * PostgreSQL wildcards (%, _) are allowed in name and combo
        * The result must match exactly one country. An exception
            will be raised if no matches or multiple matches are found
        * To construct a country without looking it up (e.g., to 
            wrap an code/name returned by a REST API call that you already
            know is correct), use the "make" method
        """

        # This uses a cache, so don't worry about it constantly calling
        # the REST API over and over
        matches = ut.lookup_country(code, name, combo)

        if not matches:
            raise ra.NotFound(f"Country not found: ({code}, {name}, {combo})")
        elif len(matches) > 1:
            raise ra.AmbiguousParameters("More than one country found for "
                    f"({code}, {name}, {combo})")

        self._data = matches[0]

    @classmethod
    def make(cls, code=None, name=None, **kwargs):
        """Create a country object without doing a lookup

        Use code and name, OR pass the node from the response object, but
        don't do both.
        """
        
        self = cls.__new__(cls)
        
        if kwargs:
            self._data = {**kwargs, "combined": f"({kwargs['code']}) {kwargs['name']}"}
        else:
            self._data = {
                    'code': code,
                    'name': name,
                    'combined': f"({code}) {name}",
                }
 
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.code == other.code
        elif isinstance(other, dict):
            # assume this is a node from a response object from the REST API
            return self.code == other.get("code", None)
        elif isinstance(other, str):
            return self.code == other 

    def __str__(self):
        return self.combo

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.code}', '{self.name}')"

    @property
    def name(self):
        return self._data["name"]
    @property
    def code(self):
        return self._data["code"]
    @property
    def combo(self):
        return self._data["combined"]
    #}}}

class Manufacturer:
    #{{{
    def __init__(self, oid=None, name=None, combo=None):
        """Lookup a manufacturer from the info provided

        * Needs at least one of oid, name, or combo. A match must satisfy
            all criteria provided, so if both oid and name are supplied,
            the manufacturer with that oid must have that name.
        * Combo is a string that contains both oid and name, e.g.,
            "(50) Acme Corporation"
        * PostgreSQL wildcards (%, _) are allowed in name and combo
        * The result must match exactly one manufacturer. An exception
            will be raised if no matches or multiple matches are found
        * To construct a manufacturer without looking it up (e.g., to 
            wrap an oid/name returned by a REST API call that you already
            know is correct), use the "make" method
        """

        # This uses a cache, so don't worry about it constantly calling
        # the REST API over and over
        matches = ut.lookup_manufacturer(oid, name, combo)

        if not matches:
            raise ra.NotFound(f"Manufacturer not found: ({oid}, {name}, {combo})")
        elif len(matches) > 1:
            raise ra.AmbiguousParameters("More than one manufacturer found for "
                    f"({oid}, {name}, {combo})")

        self._data = matches[0]

    @classmethod
    def make(cls, oid=None, name=None, /, **kwargs):
        """Create a manufacturer object without doing a lookup

        Use oid and name, OR pass the node from the response object, but
        don't do both.
        """
        self = cls.__new__(cls)
        if kwargs:
            self._data = {**kwargs, "combined": f"({kwargs['id']}) {kwargs['name']}"}
        else:
            self._data = {
                    'id': oid,
                    'name': name,
                    'combined': f"({oid}) {name}",
                }
        return self
 
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.oid == other.oid
        elif isinstance(other, dict):
            # assume this is a node from a response object from the REST API
            return self.oid == other.get("id", None)
        elif isinstance(other, int):
            return self.oid == other 

    def __str__(self):
        return self.combo

    def __repr__(self):
        return f"{self.__class__.__name__}({self.oid}, '{self.name}')"

    @property
    def name(self):
        return self._data["name"]
    @property
    def oid(self):
        return self._data["id"]
    @property
    def combo(self):
        return self._data["combined"]
    #}}}

class Institution:
    #{{{
    def __init__(self, oid=None, name=None, combo=None):
        """Lookup an institution from the info provided

        * Needs at least one of oid, name, or combo. A match must satisfy
            all criteria provided, so if both oid and name are supplied,
            the institution with that oid must have that name.
        * Combo is a string that contains both oid and name, e.g.,
            "(186) University of Minnesota Twin Cities"
        * PostgreSQL wildcards (%, _) are allowed in name and combo
        * The result must match exactly one institution. An exception
            will be raised if no matches or multiple matches are found
        * To construct an institution without looking it up (e.g., to 
            wrap an oid/name returned by a REST API call that you already
            know is correct), use the "make" method
        """

        # This uses a cache, so don't worry about it constantly calling
        # the REST API over and over
        matches = ut.lookup_institution(oid, name, combo)

        if not matches:
            raise ra.NotFound(f"Institution not found: ({oid}, {name}, {combo})")
        elif len(matches) > 1:
            raise ra.AmbiguousParameters("More than one institution found for "
                    f"({oid}, {name}, {combo})")

        self._data = matches[0]

    @classmethod
    def make(cls, oid=None, name=None, **kwargs):
        """Create an institution object without doing a lookup

        Use oid and name, OR pass the node from the response object, but
        don't do both.
        """
        
        self = cls.__new__(cls)
        
        if kwargs:
            self._data = {**kwargs, "combined": f"({kwargs['id']}) {kwargs['name']}"}
        else:
            self._data = {
                    'id': oid,
                    'name': name,
                    'combined': f"({oid}) {name}",
                }
 
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.oid == other.oid
        elif isinstance(other, dict):
            # assume this is a node from a response object from the REST API
            return self.oid == other.get("id", None)
        elif isinstance(other, int):
            return self.oid == other 

    def __str__(self):
        return self.combo

    def __repr__(self):
        return f"{self.__class__.__name__}({self.oid}, '{self.name}')"

    @property
    def name(self):
        return self._data["name"]
    @property
    def oid(self):
        return self._data["id"]
    @property
    def combo(self):
        return self._data["combined"]
    #}}}

class User:
    #{{{
    ...
    #}}}

class Role:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("No lookup available. Use Role.make() to construct from data.")

    @classmethod
    def make(cls, **kwargs):
        self = cls.__new__(cls)
        self._data = {**kwargs, "combined": f"({kwargs['id']}) {kwargs['name']}"}
        return self

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.oid == other.oid
        elif isinstance(other, dict):
            # assume this is a node from a response object from the REST API
            return self.oid == other.get("id", None)
        elif isinstance(other, int):
            return self.oid == other 

    def __str__(self):
        return self.combo

    def __repr__(self):
        return f"{self.__class__.__name__}({self.oid}, '{self.name}')"

    @property
    def name(self):
        return self._data["name"]
    @property
    def oid(self):
        return self._data["id"]
    @property
    def combo(self):
        return self._data["combined"]





