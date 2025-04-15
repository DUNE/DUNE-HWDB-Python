#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/HWDBUtility/TypeCheck.py
Copyright (c) 2024 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy

!!!!!!!!!!!!
NOTICE: These comments were written a while ago and may not be current!
!!!!!!!!!!!!

casting types
-------------
any
    use value as interpreted by Pandas. Convert NaN to null
    TODO: might need to do something about those nasty "numpy.Int64's" that
    can't be left alone if you want to slap it into JSON anywhere.

string or str
    use str(value). Convert NaN to null, give warning
integer or int
    use int(value). Convert NaN to null, give warning
    warn if casting truncates value
float
    use float(value). Convert NaN to null, give warning

number
    Attempt to cast as int. If unsuccessful, attempt to cast as float.

bool
    converts "true", "false", 0, 1, "yes", or "no" (all case-insensitive) to bool,
    warn if anything else

null or none
    null if value==NaN. otherwise, use value as interpreted by Pandas and warn
    (Pandas will set blanks to NaN, so use this to make them null instead)

nan
    NaN if value==NaN, otherwise cast to string and warn

empty
    "" if value==NaN, otherwise cast to string and warn


array or list
    use json.loads(value), warn if result type is not list, convert NaN to null.
object or obj or dict
    use json.loads(value), warn if result type is not dict, convert NaN to null.
json
    use json.loads(value), convert NaN to null.

type1,type2[,type3[...]]
    cast as type1. if casting gives warning, cast as type2. repeated as necessary.

array<[subtype]>
object<[subtype]><[subtype]>
    possible future enhancement.
    For now, ignores subtypes

group
    this "type" does not correspond to a column in the sheet.
    instead, it creates a group and defines which columns will be
    subordinate to this group.

"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

#import Sisyphus.RestApiV1 as ra
#import Sisyphus.RestApiV1.Utilities as ut

import json
import sys
import numpy as np
import pandas as pd
import os
from copy import deepcopy
import re
import math
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field
from collections import namedtuple

CastWarning = namedtuple("CastResult", ["dtype", "reason"])
CastResult = namedtuple("CastResult", ["warnings", "original_value", "value"])


CellLocation = namedtuple("CellLocation", ["column", "row"])

@dataclass
class Cell:
    """Class for holding a cell's contents, plus tracking information"""
    source: str
    location: CellLocation = None
    warnings: list = field(default_factory=list)
    datatype: str = None
    value: 'typing.Any' = None



# list of string to interpret a an empty/null/nan when asked explicity to
# convert to one of those types.
null_sentinels = ("", "na", "nan", "none", "nothing", "notanumber", "null")

def isnan(value):
    #{{{
    # Annoyingly, math.isnan() requires the argument to be a float or
    # castable as a float. It raises a TypeError if it's something
    # else, e.g., a string.
    return (type(value) is float and math.isnan(value))
    #}}}

def can_cast_null(value):
    return (
        value is None 
        or isnan(value)
        or str(value).lower() in null_sentinels)

def cast_generic_blank(cell, blank_type_name, blank_type_value):
    #{{{
    cell = deepcopy(cell)
    if can_cast_null(cell.value):
        # This is a successful cast. No warnings.
        cell.value = blank_type_value
        cell.warnings = []
        return cell
    else:
        cell.warnings.append(
                f"'{cell.value}' is not interpretable as {blank_type_name}")
        return cell
    #}}}

def cast_null(cell):
    return cast_generic_blank(cell, "null", None)
def cast_empty(cell):
    return cast_generic_blank(cell, "empty", "")
def cast_nan(cell):
    return cast_generic_blank(cell, "nan", math.nan)

def cast_str(cell):
    #{{{
    # As far as I know, anything can be cast to as string. So just do it.
    cell = deepcopy(cell)
    cell.value = str(cell.value)
    cell.warnings = []
    return cell
    #}}}

def cast_int(cell):
    #{{{
    cell = deepcopy(cell)
    if type(cell.value) in (int, np.int64):
        cell.value = int(cell.value)
        cell.warnings = []
        return cell

    if type(cell.value) in (float, np.float64):
        if isnan(cell.value):
            cell.warnings.append("cannot interpret NaN as int")
            return cell
        elif cell.value - float(int(cell.value)) == 0.0:
            cell.value = int(cell.value)
            cell.warnings = []
            return cell
        else:
            cell.warnings.append(f"interpreting '{cell.value}' as int would truncate value")
            return cell

    if type(cell.value) not in (str,):
        cell.warnings.append(f"cannot interpret '{cell.value}' as int") 
        return cell

    # The remainder of this function tries to interpret a string as an int
    try:
        cell.value = int(cell.value)
        cell.warnings = []
        return cell
    except (TypeError, ValueError) as err:
        pass

    try:
        # strings like "143.0" or "1e9" won't cast as int, but seem like they
        # should be valid, as long as there's no truncation error
        value = float(cell.value)
        if isnan(value):
            cell.warnings.append(f"cannot interpret '{cell.value}' as int")
            return cell
        elif value - float(int(value)) == 0.0:
            cell.value = value
            cell.warnings = []
            return cell
        else:
            cell.warnings.append(f"interpreting '{cell.value}' as int would truncate value")
            return cell
    except (TypeError, ValueError) as err:
        pass

    # TODO: Maybe interpret hex (0xff), oct (0o377) or bin (0b11111111)
    # or maybe use ast.literal_eval. But for now, just give up.

    cell.warnings.append(f"Could not interpret '{cell.value}' as int")
    return cell
    #}}}

def cast_unixtime(cell):
    #{{{
    
    cell = deepcopy(cell)
    cell_original = deepcopy(cell)

    cell.warnings = []
    cell = cast_number(cell)
    if len(cell.warnings) > 0:
        cell_original.warnings.append(f"Cannot interpret '{cell_original.value}' as "
                "Unix time")
        return cell

    cell.value = datetime.fromtimestamp(cell.value).isoformat()
    return cell
    #}}}

def cast_float(cell):
    #{{{
    # For the purposes of this module, NaN is not considered a valid float,
    # even though it is of type float. To get it to accept NaN without warnings,
    # make the type "float,nan", so it can fall back to NaN.
    
    cell = deepcopy(cell)
    
    if type(cell.value) in (float, np.float64, int, np.int64): 
        if not isnan(cell.value):
            cell.value = float(cell.value)
            return cell
        cell.warnings.append("value is NaN")
        return cell
    
    if type(cell.value) not in (str,):
        cell.warnings.append(f"cannot interpret '{cell.value}' as int")
        return cell
    
    try:
        cell.value = float(cell.value)
        cell.warnings = []
        return cell 
    except (TypeError, ValueError) as err:
        pass
    
    cell.warnings.append(f"Could not interpret '{cell.value}' as int")
    return cell
    #}}}

def cast_number(cell):
    #{{{
    # Try casting this to an int. If that fails, try as a float. Only
    # return the warnings from the float.
    cell = deepcopy(cell)
    cell_copy = deepcopy(cell)
    cell_copy.warnings = []
    cell_copy = cast_int(cell_copy)
    if len(cell_copy.warnings) == 0:
        return cell_copy

    return cast_float(cell)


    #}}}

def cast_bool(cell):
    #{{{
    # Interpret 0, False, "false", "f", "no", or "n" as False
    # Interpret 1, True, "true", "t", "yes", or "y" as True
    # String values are not case-sensitive

    cell = deepcopy(cell)
    
    if str(cell.value).lower() in ("0", "0.0", "false", "f", "no", "n"):
        cell.value = False
        cell.warnings = []
        return cell

    if str(cell.value).lower() in ("1", "1.0", "true", "t", "yes", "y"):
        cell.value = True
        cell.warnings = []
        return cell

    cell.warnings.append(f"cannot interpret '{cell.value}' as bool")
    return cell
    #}}}

def cast_list(cell):
    #{{{
    cell = deepcopy(cell)
    try:
        value = json.loads(str(cell.value))
        if type(value) is list:
            cell.value = value
            return cell
    except json.JSONDecodeError as err:
        pass

    cell.warnings.append(f"cannot interpret '{cell.value}' as list")
    return cell
    #}}}

def cast_dict(cell):
    #{{{
    cell = deepcopy(cell)
    try:
        value = json.loads(str(cell.value))
        if type(value) is dict:
            cell.value = value
            return cell
    except json.JSONDecodeError as err:
        pass    
    cell.warnings.append(f"cannot interpret '{cell.value}' as dict")
    return cell
    #}}}

def cast_json(cell):
    #{{{
    cell = deepcopy(cell)
    try:
        cell.value = json.loads(str(cell.value))
        return cell
    except json.JSONDecodeError as err:
        pass    
    cell.warnings.append(f"cannot interpret '{cell.value}' as json")
    return cell
    #}}}

def cast_any(cell):
    #{{{
    # We'll do our best here to just return the data as whatever type
    # pandas gave it, but we'll have to change the numpy types to 
    # their python equivalent so that json doesn't choke on it. I'm 
    # figuring that if it's a string and it checks out as a dict or 
    # list, we might as well do that as well. Otherwise, it should
    # just leave it as it is.
    # This shouldn't return any warnings.
    cell = deepcopy(cell)

    try:
        value = json.loads(str(cell.value))
        if type(value) in (dict, list):
            cell.value = value
            cell.warnings = []
            return cell
    except json.JSONDecodeError as err:
        pass    

    if type(cell.value) in (np.int64,):
        cell.value = int(cell.value)
    elif type(cell.value) in (np.float64,):
        cell.value = float(cell.value)
    elif type(cell.value) in (np.bool_,):
        cell.value = bool(cell.value)

    cell.warnings = []
    return cell

    #}}}

def cast(cell):
    #{{{
    # If the value is literally "<null>", treat this as an overwriting null.
    # We really needed there to be two kinds of nulls. One that's just a plain 
    # old ordinary null, and another that means that if you're editing an item,
    # keep the current value. Treat "<null>" as the second kind.
    
    if type(cell.value) in (str,):
        if cell.value.casefold() in ("<null>", "<unassigned>"):
            cell.value = "<null>"
            return cell
        elif cell.value.casefold() == "<empty>":
            cell.value = "<empty>"
            return cell
        elif cell.value.casefold() == "<nan>":
            cell.value = "<nan>"
            return cell

    type_chain = cell.datatype.lower().split(',')

    for typedef in type_chain:
        if typedef in ('str', 'string', 'text'):
            cell = cast_str(cell)
        elif typedef in ('int', 'integer'):
            cell = cast_int(cell)
        elif typedef in ('float', 'real'):
            cell = cast_float(cell)
        elif typedef in ('number', 'numeric'):
            cell = cast_number(cell)
        elif typedef in ('unixtime',):
            cell = cast_unixtime(cell)
        elif typedef in ('bool', 'boolean', 'bit'):
            cell = cast_bool(cell)
        elif typedef in ('null', 'none'):
            cell = cast_null(cell)
        elif typedef in ('empty',):
            cell = cast_empty(cell)
        elif typedef in ('nan',):
            cell = cast_nan(cell)
        elif typedef in ('list', 'array'):
            cell = cast_list(cell)
        elif typedef in ('dict', 'obj', 'object'):
            cell = cast_dict(cell)
        elif typedef in ('json',):
            cell = cast_json(cell)
        elif typedef in ('any'):
            cell = cast_any(cell)
        else:
            cell = cast_any(cell)
            cell.warnings.append(f"Unknown type '{typedef}'")
        if not cell.warnings:
            break

    return cell
    #}}}

