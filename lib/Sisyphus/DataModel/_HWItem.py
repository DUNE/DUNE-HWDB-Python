#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/DataModel/_HWItem.py
Copyright (c) 2024 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

import Sisyphus.RestApiV1 as ra
import Sisyphus.RestApiV1.Utilities as ut
from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus.Utils.Terminal.BoxDraw import Table
from Sisyphus.Utils.Terminal import BoxDraw
from Sisyphus.Utils import utils

from Sisyphus.Utils.utils import preserve_order, restore_order, serialize_for_display
import io
import json
import sys
import os
from copy import deepcopy
import re
import time
import random
from datetime import datetime

_HWItem_cache = {}

class HWItem:
    #{{{
    #{{{
    # Map the "column" name to the "property" name
    _column_to_property = \
    {
        "Part Type ID": "part_type_id",
        "Part Type Name": "part_type_name",
        "Serial Number": "serial_number",
        "External ID": "part_id",
        "Institution": "institution",
        "Institution Name": "institution_name",
        "Institution ID": "institution_id",
        "Country": "country",
        "Country Name": "country_name",
        "Country Code": "country_code",
        "Manufacturer": "manufacturer",
        "Manufacturer Name": "manufacturer_name",
        "Manufacturer ID": "manufacturer_id",
        "Comments": "comments",
        "Subcomponents": "subcomponents",
        "Specifications": "specifications",
        "Status": "status",
        'Location': "location", 
        'Location ID': "location_id", 
        'Location Name': "location_name",
        #'Location Country': "location_country", 
        #'Location Country Code': "location_country_code", 
        #'Location Country Name': "location_country_name", 
        'Location Comments': "location_comments",
        "Arrived": "arrived",
    }
    _property_to_column = {v: k for k, v in _column_to_property.items()}
    #}}}

    # TODO: we need a bunch of property getters/setters, but 
    # we can get away without them for a while because we
    # aren't using this interactively.
    #{{{
    @property
    def part_type_id(self):
        return self._current['part_type_id']

    @property
    def part_type_name(self):
        return self._current['part_type_name']

    @property
    def part_id(self):
        return self._current['part_id']
    
    @property
    def serial_number(self):
        return self._current['serial_number']
    @serial_number.setter
    def serial_number(self, value):
        self._current['serial_number'] = value
    
    @property
    def country_code(self):
        return self._current['country_code']
    @property
    def country_name(self):
        return self._current['country_name']
    @property
    def country(self):
        return self._current['country']
    
    @property
    def institution_id(self):
        return self._current['institution_id']
    @property
    def institution_name(self):
        return self._current['institution_name']
    @property
    def institution(self):
        return self._current['institution']
    
    @property
    def manufacturer_id(self):
        return self._current['manufacturer_id']
    @property
    def manufacturer_name(self):
        return self._current['manufacturer_name']
    @property
    def manufacturer(self):
        return self._current['manufacturer']

    @property
    def specifications(self):
        return self._current['specifications']


    @property
    def location(self):
        return self._current["location"]
    @property
    def location_id(self):
        return self._current["location_id"]
    @property
    def location_name(self):
        return self._current["location_name"]
    #@property
    #def location_country(self):
    #    return self._current["location_country"]
    #@property
    #def location_country_code(self):
    #    return self._current["location_country_code"]
    #@property
    #def location_country_name(self):
    #    return self._current["location_country_name"]
    @property
    def location_comments(self):
        return self._current["location_comments"]
    @property
    def arrived(self):
        return self._current["arrived"]

    @property
    def status(self):
        return self._current["status"]
    
    @property
    def comments(self):
        return self._current["comments"]

    @property
    def subcomponents(self):
        return self._current["subcomponents"]

    # TODO: add more of these
    #}}}

    #--------------------------------------------------------------------------

    def __init__(self, *, part_type_id=None, part_type_name=None, AreYouSure=False):
        #{{{
        """Do not create new HWItem instances directly!

        The object needs to know where the data came from in order to
        function correctly. Use "fromUserData" to create a new instance
        from a user source such as a spreadsheet, and "fromHWDB" to pull
        an existing HWItem from the database.
        """        
        if not AreYouSure:
            raise ValueError("Don't create new HWItems this way "
                            "unless you know what you're doing!")
        
        self._part_type = ut.fetch_component_type(part_type_id, part_type_name)
        self._last_commit = {k: None for k in self._property_to_column.keys()}
        self._last_commit['part_type_id'] = self._part_type['ComponentType']['part_type_id']
        self._last_commit['part_type_name'] = self._part_type['ComponentType']['full_name']
        self._current = deepcopy(self._last_commit)
        self._is_new = False    
        #}}}
    #--------------------------------------------------------------------------

    def toUserData(self):
        user_record = {col_name: self._current[prop_name] 
                for col_name, prop_name in self._column_to_property.items()}
        return user_record

    #--------------------------------------------------------------------------

    @classmethod
    def fromUserData(cls, user_record, encoder=None):
        #{{{ method
        #{{{ docstring
        """Create a HWItem from user data

        Typically, this means the data read from a spreadsheet and encoded
        by an Encoder.

        After creating the HWItem instance, it will attempt to find the item
        in the HWDB using the External ID or the Part Type and Serial Number.
        If it is found, it will keep an internal copy of the data in the
        HWDB so that it can be determined whether the data has changed and 
        needs to be updated.

        Because the REST API does not provide a means of updating the entire
        HWItem all at once, there are several methods for checking for changes
        and for making updates. This is helpful if you are adding a bunch of
        HWItems at the same time, and subcomponents for this HWItem may not 
        have been added yet. I.e., you can just update the 'core' part of the
        data and come back to finish it after all the other items have been
        added.

        "record" format:
        ================
        {
            "Part Type ID": "Z00100300022",
            "Part Type Name": "Z.Sandbox.HWDBUnitTest.biff",
            "Serial Number": "059313D3-B728-4C3D-857C-1AB9DAC93232",
            "External ID": "Z00100300022-00057",
            "Institution ID": 186,
            "Institution Name": "University of Minnesota Twin Cities",
            "Country Name": "United States",
            "Country Code": "US",
            "Manufacturer ID": 7,
            "Manufacturer Name": "Hajime Inc",
            "Comments": "generated 2023-10-17 09:39:48",
            "Status": "Available",
            "Specifications": [
                {
                    "Height": 97.42,
                    "Length": 119.76,
                    "Width": 85.56
                }
            ],
            "Subcomponents": [
                {
                    "Left Bongo": "Z00100300023-00104",
                    "Right Bongo": "Z00100300023-00105"
                }
            ],
            "Country": "(US) United States",
            "Institution": "(186) University of Minnesota Twin Cities",
            "Manufacturer": "(7) Hajime Inc"
        }

        It is not necessary to provide both "Country" fields or all three
        "Institution" or "Manufacturer" fields. Just enough to look it up
        and identify it uniquely. 
        
        "Manufacturer" is entirely optional, but if you intend to leave it 
        blank, none of the fields should be given or should be given as None.

        If "Country" is not provided, it will be inferred from "Institution".

        Specifications and Subcomponents are expected to be lists containing
        a single dictionary, because it will come out of the Encoder that way,
        but the dictionary can also be supplied directly without being 
        enclosed in a list. Either way, it will be stored internally without
        the enclosing list.
        """
        #}}} docstring

        logger.debug(f"user_record: {user_record}")

        new_hwitem = HWItem(
                part_type_id=user_record.get("Part Type ID", None),
                part_type_name=user_record.get("Part Type Name", None),
                AreYouSure=True)

        user_record = deepcopy(user_record)
        
        #print(json.dumps(user_record, indent=4))

        if isinstance(spec := user_record.get("Specifications", None), list):
            user_record["Specifications"] = spec[-1]

        if isinstance(subcomp := user_record.get("Subcomponents", None), list):
            user_record["Subcomponents"] = subcomp[0]

        try:
            hwdb_record = cls._get_from_hwdb(
                    part_type_id=user_record.get("Part Type ID", None),
                    part_type_name=user_record.get("Part Type Name", None),
                    part_id=user_record.get("External ID", None),
                    serial_number=user_record.get("Serial Number", None))
            new_hwitem._is_new = False
            new_hwitem._last_commit = hwdb_record
        except ra.NotFound:
            if cls._is_unassigned(user_record.get("External ID", None)):
                # This is fine. It just means that it's new!
                new_hwitem._is_new = True
            else:
                raise    

        for col_name, prop_name in cls._column_to_property.items():
            if col_name not in user_record:
                logger.warning(f"{col_name} not in user_record")
            else:
                new_hwitem._current[prop_name] = user_record.pop(col_name)

        if len(user_record) > 0:
            logger.warning(f"extra columns in user_record: {tuple(user_record.keys())}")

        new_hwitem.normalize()

        # if the serial number has changed, we need to check whether it's
        # already in use, since we didn't search on it because we already
        # had the part_id. If it's in use, it's not necessarily a problem,
        # if the item using it is also changing to something else. Just
        # search for it and record it for later.
        new_SN = new_hwitem._current["serial_number"]
        existing_SN = new_hwitem._last_commit["serial_number"]

        new_hwitem._sn_conflicts = []
        
        if (not new_hwitem._is_new) and (new_SN is not None) and (existing_SN != new_SN):
            # Find the conflicts, only if we're changing the SN, and we're 
            # changing it to something besides None
            try:
                more_records = ut.fetch_hwitems(
                            part_type_id=new_hwitem._current['part_type_id'],
                            serial_number=new_SN)

                new_hwitem._sn_conflicts = list(more_records.keys())
            except ra.NotFound:
                pass 

        #csn, nsn = new_hwitem._last_commit['serial_number'], new_hwitem._current['serial_number']
        #print(csn, nsn, new_hwitem._current['comments'])
        #print('\n\n\n')

        return new_hwitem
        #}}} method

    #--------------------------------------------------------------------------

    @classmethod
    def fromHWDB(cls, part_type_id=None, part_type_name=None, part_id=None, serial_number=None):
        #{{{
        """Create a new HWItem instance by downloading an item from the HWDB

        The arguments supplied must be sufficient to uniquely describe one
        item in the HWDB.
        """
        
        hwdb_record = cls._get_from_hwdb(part_type_id, part_type_name, part_id, serial_number)
        new_hwitem = HWItem(
                part_type_id=hwdb_record.get("part_type_id", None),
                part_type_name=hwdb_record.get("part_type_name", None),
                AreYouSure=True)

        new_hwitem._last_commit = deepcopy(hwdb_record)
        new_hwitem._current = deepcopy(hwdb_record)
        
        return new_hwitem
        #}}}
    #--------------------------------------------------------------------------

    @classmethod
    def _get_from_hwdb(cls, part_type_id=None, part_type_name=None, part_id=None, serial_number=None):
        #{{{
        """(internal method) Load HWItem data from the HWDB"""

        kwargs = {
            "part_type_id": part_type_id,
            "part_type_name": part_type_name,
            "part_id": part_id,
            "serial_number": serial_number,
            "count": 2
        }
        # If there's a part_id, don't use the serial_number, because it's
        # possible that the user has given one with the intent of changing
        # it to the new one.
        if cls._is_unassigned(part_id):
            kwargs['part_id'] = None
        else:
            kwargs["serial_number"] = None
        
        hwitem_raw = ut.fetch_hwitems(**kwargs)

        logger.info(f"raw item data:\n{json.dumps(hwitem_raw,indent=4)}")

        # Raise an exception if no records are found, or more than one is found.
        if len(hwitem_raw) == 0:
            raise ra.NotFound("The arguments provided did not match any HWItems.")
        elif len(hwitem_raw) > 1:
            # TODO: we could still cache it for later.
            logger.warning(json.dumps(hwitem_raw, indent=4))
            raise ra.AmbiguousParameters("The arguments provided matched more than one HWItem.")

      
        # We still need a bit of extra data before we can create the record  
        _, item_node = hwitem_raw.popitem()
        it = item_node["Item"]
        sc = item_node["Subcomponents"]
        loc_list = item_node["Locations"] 
        if len(loc_list) == 0:
            loc = None
        else:
            loc = loc_list[0]
        ct_all = ut.fetch_component_type(part_type_id=it["component_type"]["part_type_id"])
        ct = ct_all["ComponentType"]
       
        country_info = ut.lookup_country(it["country_code"])[0]

        hwdb_record = (
        {
            "part_type_id": ct["part_type_id"],
            "part_type_name": ct["full_name"],
            "serial_number": it["serial_number"],
            "part_id": it["part_id"],
            "institution_id": it["institution"]["id"],
            "institution_name": it["institution"]["name"],
            #"country_name": ut.lookup_country_name_by_country_code(it["country_code"]),
            "country_name": country_info['name'],
            #"country_code": it["country_code"],
            "country_code": country_info['code'],
            "country": country_info['combined'],
            "comments": it["comments"],
            "status": it["status"]["id"],
        })
        #hwdb_record["country"] = (f"({hwdb_record['country_code']}) "
        #                            f"{hwdb_record['country_name']}")
        hwdb_record["institution"] = (f"({hwdb_record['institution_id']}) "
                                    f"{hwdb_record['institution_name']}")
            
        if it["manufacturer"] is None:
            hwdb_record["manufacturer_id"] = None
            hwdb_record["manufacturer_name"] = None
            hwdb_record["manufacturer"] = None
        else:
            hwdb_record["manufacturer_id"] = it["manufacturer"]["id"]
            hwdb_record["manufacturer_name"] = it["manufacturer"]["name"]
            hwdb_record["manufacturer"] = (f"({hwdb_record['manufacturer_id']}) "
                                    f"{hwdb_record['manufacturer_name']}")

        # Location
        if loc is None:
            hwdb_record["location_id"] = None
            hwdb_record["location_name"] = None
            hwdb_record["location"] = None
            hwdb_record["location_comments"] = None
            hwdb_record["arrived"] = None
        else:
            hwdb_record["location_id"] = loc["location"]["id"]
            hwdb_record["location_name"] = loc["location"]["name"]
            hwdb_record["location"] = f"({loc['location']['id']}) {loc['location']['name']}"
            hwdb_record["location_comments"] = loc["comments"]
            hwdb_record["arrived"] = loc["arrived"]
            


        # Specifications
        #print(json.dumps(ct_all, indent=4))
        #spec_def = ct_all["ComponentType"]["properties"]["specifications"][-1]["datasheet"]
        

        hwdb_record["specifications"] = utils.restore_order(deepcopy(it["specifications"][-1]))
        _ = hwdb_record["specifications"].pop("_meta", None)
      
        #meta = deepcopy(it["specifications"][-1].get("_meta", None))
        #if meta:
        #    hwdb_record["specifications"]["_meta"] = meta

        # Subcomponents
        default_subcomps = {k: None for k in ct_all["ComponentType"]["connectors"].keys()}
        subcomps = {k:v for k, v in sorted
                            ([(x["functional_position"], x["part_id"]) for x in sc])}
        hwdb_record["subcomponents"] = {**default_subcomps, **subcomps}

        return hwdb_record
        #}}}
    
    #--------------------------------------------------------------------------

    @classmethod
    def user_role_check(cls, part_type_id=None, part_type_name=None):
        #{{{
        """Checks if the user is permitted to work with this ComponentType"""
        # TODO: maybe this needs to be part of a ComponentType class instead?

        return ut.user_role_check(part_type_id, part_type_name)
        #}}}


    #--------------------------------------------------------------------------
    def is_new(self):
        """Tell whether this HWItem is new and is not in the HWDB yet"""
        return self._is_new
    #--------------------------------------------------------------------------
    
    def update_location(self):
        last_commit = self._last_commit
        current = self._current

        # Update only if "location" is present AND any one of the three fields
        # has changed value, i.e., don't update if it hasn't been changed.

        if current['location'] is None:
            return

        if current['location'] == last_commit['location'] \
                and current['arrived'] == last_commit['arrived'] \
                and current['location_comments'] == last_commit['location_comments']:
            return

        part_id = current['part_id']
        post_data = {
            "arrived": current['arrived'],
            "comments": current['location_comments'],
            "location": {
                "id": current['location_id']
            }
        }
        
        ra.post_hwitem_location(part_id, post_data)


    #--------------------------------------------------------------------------

    def update_core(self):
        #{{{
        """Update the 'core' properties of this HWItem in the HWDB

        The 'core' properties are those properties that can be updated by the
        main REST API call, and does not include subcomponents.
        """ 

        last_commit = self._last_commit
        current = self._current
       
        ct_all = ut.fetch_component_type(part_type_id=current['part_type_id'])
        ct = ct_all["ComponentType"]
        spec_def = ct['properties']['specifications'][-1]['datasheet']
        
        if self.is_new():
            post_data = {
                "component_type": {"part_type_id": current['part_type_id']},
                "country_code": current['country_code'],
                "institution": {"id": current['institution_id']},
                "serial_number": current['serial_number'],
                "manufacturer": {"id": current['manufacturer_id']},
                "specifications": utils.preserve_order(current['specifications']),
                "status": {"id": current['status']},
                "comments": current['comments'],
                #"subcomponents": current['subcomponents']
            }

            if '_meta' in spec_def:
                post_data['specifications'].setdefault('_meta', {})
            else:
                _ = post_data['specifications'].pop('_meta', None)

            logger.info("Posting new item")
            resp = ra.post_hwitem(part_type_id=current['part_type_id'], data=post_data)
            self._is_new = False

            current["part_id"] = resp["part_id"]
           
            fields_to_copy = [
                "part_id", "part_type_name", "part_type_id", "serial_number",
                "comments", "country", "country_name", "country_code",
                "institution", "institution_id", "institution_name",
                "manufacturer", "manufacturer_id", "manufacturer_name",
                "specifications", "status" #, "location", "location_id", "location_name",
                #"location_comments", "arrived"
            ]

            for field in fields_to_copy:
                last_commit[field] = current[field]
        else:
            
            patch_data = {
                "part_id": current['part_id'],
                "serial_number": current['serial_number'],
                "manufacturer": {"id": current['manufacturer_id']},
                "specifications": utils.preserve_order(current['specifications']),
                "status": {"id": current['status']},
                "comments": current['comments'],
            }        
            
            if "_meta" in spec_def:
                patch_data['specifications'].setdefault('_meta', {})
            else:
                _ = patch_data['specifications'].pop('_meta', None)

            logger.info("Patching item")
            resp = ra.patch_hwitem(part_id=current['part_id'], data=patch_data)
            
            fields_to_copy = [
                "serial_number", "comments", "manufacturer", "manufacturer_id", 
                "manufacturer_name", "specifications", "status"
            ]
            
            for field in fields_to_copy:
                last_commit[field] = current[field]


        #}}}


    #--------------------------------------------------------------------------

    def update_enabled(self):
        #{{{
        """Update the 'enabled' property of this HWItem in the HWDB"""

        logger.info(f"Committing item:\n{self}")

        if self.enabled_has_changed():
            current = self._current     
            resp = ut.enable_hwitem(current['part_id'], 
                        enable=(current['enabled']==1), 
                        comments=current['comments'])  
        #}}}

    #--------------------------------------------------------------------------
    
    def release_subcomponents(self):
        #{{{
        """Release subcomponents used by this item

        Only subcomponents that are going to be swapped for a different
        one should be released. This is so that other items can pick it
        up if they want
        """

        self.normalize_subcomponents()

        old_subcomps = self._last_commit['subcomponents']
        new_subcomps = self._current['subcomponents']

        dicts_are_equal = True
        release_dict = {}
        keys = set(old_subcomps).union(set(new_subcomps))
        for key in keys:
            if old_subcomps.get(key, None) != new_subcomps.get(key, None):
                dicts_are_equal = False
                release_dict[key] = None
            else:
                release_dict[key] = old_subcomps.get(key, None)
        if dicts_are_equal:
            logger.debug(f"{self.part_id}: No changes in subcomps")
            return

        payload = {
            "component": {"part_id": self.part_id},
            "subcomponents": release_dict,
        }

        resp = ra.patch_subcomponents(self.part_id, payload)
        #}}}

    #--------------------------------------------------------------------------

    def normalize_subcomponents(self):
        #{{{
        """Look up any subcomponents that are using a serial number instead of a part id"""

        def is_valid_part_id(part_type_id, s):
            if type(s) is not str:
                return False
            pattern = re.compile(''.join([part_type_id, '-', '[0-9]{5}']))
            if pattern.match(s):
                return True
            return False

        #print(json.dumps(self._last_commit, indent=4))
        #print(json.dumps(self._current, indent=4))


        subcomp_def = self._part_type["ComponentType"]["connectors"]
        old_subcomps = self._last_commit['subcomponents']
        new_subcomps = self._current['subcomponents']

        if old_subcomps is None:
            old_subcomps = self._last_commit['subcomponents'] = {}

        for func_pos, part_type_id in subcomp_def.items():
            #print(f"Functional Position: {func_pos}")
            #print(f"Part Type ID: {part_type_id}")
            last_part_id = old_subcomps.setdefault(func_pos, None)
            next_part_id = new_subcomps.setdefault(func_pos, None) # note, could be a serial number!
            #print(f"Last Committed Part ID: {old_subcomps[func_pos]}")
            #print(f"New Part ID: {new_subcomps[func_pos]}")
            
            if next_part_id in (None, ""):
                new_subcomps[func_pos] = None

            elif not is_valid_part_id(part_type_id, next_part_id):                
                lookup = ut.fetch_hwitems(part_type_id=part_type_id, serial_number=next_part_id)

                if len(lookup) == 0:
                    raise ra.NotFound(f"Could not attach subcomponent '{next_part_id}' to "
                            f"{self.part_id} because the serial number cannot be found.")
                elif len(lookup) > 1:
                    raise ra.AmbiguousParameters("Could not attach subcomponent '{next_part_id}' to "
                            f"{self.part_id} because the serial number is ambiguous.")
                
                # We found it! So we can change our new one to be a part_id.
                new_part_id = new_subcomps[func_pos] = list(lookup.keys())[0] 
        #}}}

    #--------------------------------------------------------------------------
    
    def update_subcomponents(self):
        #{{{
        """Update the subcomponents for this HWItem"""
        
        old_subcomps = self._last_commit['subcomponents']
        new_subcomps = self._current['subcomponents']

        dicts_are_equal = True
        release_dict = {}
        keys = set(old_subcomps).union(set(new_subcomps))
        for key in keys:
            if old_subcomps.get(key, None) != new_subcomps.get(key, None):
                dicts_are_equal = False
                break
        if dicts_are_equal:
            logger.debug(f"{self.part_id}: No changes in subcomps")
            return

        payload = {
            "component": {"part_id": self.part_id},
            "subcomponents": new_subcomps,
        }

        resp = ra.patch_subcomponents(self.part_id, payload)
        #}}}

    #--------------------------------------------------------------------------
    
    def normalize(self):
        #{{{
        """Fills in fields whose values can be automatically derived

        If only partial information is supplied for Institution, Country,
        or Manufacturer, but enough information is provided to fill in the
        rest, do it. (E.g., manufacturer_id is enough to find the name and
        the combo id/name field.)

        If an existing record exists for the item, fill in null fields with
        the existing values. If the field is explicitly "<null>", however,
        use this as an indicator to actually set it to null instead.
        """

        def literal_null_check(s):
            # check if 's' is <null> or <empty> and return None or "" in
            # its place. Otherwise just return 's' as-is.
            if s == "<null>":
                return None
            elif s == "<empty>":
                return ""
            elif s == "<nan>":
                return float('nan')
            else:
                return s

        last_commit = self._last_commit
        current = self._current

        # Normalize EXTERNAL ID
        # because this might have been looked up by serial number
        if not self.is_new():
            current['part_id'] = last_commit['part_id']


        # Normalize INSTITUTION
        if current["institution"] or current["institution_name"] or current["institution_id"]:
            inst = ut.lookup_institution(
                        institution_id=current["institution_id"], 
                        institution_name=current["institution_name"],
                        institution=current["institution"])
            if len(inst) == 1:
                current["institution_id"] = inst[0]['id']
                current["institution_name"] = inst[0]['name']
                current["institution"] = inst[0]['combined']
            elif len(inst) == 0:
                raise ra.NotFound("No Institutions match the criteria given.")
            else:
                raise ra.AmbiguousParameters("The fields for Institution do not uniquely "
                            "identify a single Institution")
            if not self.is_new() and current['institution'] != last_commit['institution']:
                #logger.error(f"{current['institution']} != {last_commit['institution']}")
                #logger.info(f"{json.dumps(last_commit, indent=4)}")
                raise ValueError("The Institution for an Item cannot be edited.")
       
        elif not self.is_new():
            current["institution_id"] = last_commit['institution_id']
            current["institution_name"] = last_commit['institution_name']
            current["institution"] = last_commit['institution']
        else:
            raise ValueError("Items require an Institution to be specified.")

        # Normalize LOCATION
        if current['location'] or current['location_name'] or current['location_id'] \
                    or current['arrived'] or current['location_comments']:

            if current['location'] or current['location_name'] or current['location_id']:
                loc = ut.lookup_institution(
                            institution_id=current['location_id'],
                            institution_name=current['location_name'],
                            institution=current['location'])
                if len(loc) == 0:
                    raise ra.NotFound("No locations match the criteria given.")
                elif len(loc) > 1:
                    raise ra.AmbiguousParameters("The fields for Location do not uniquely "
                                "identify a single Location")
                current["location_id"] = loc[0]['id']
                current['location_name'] = loc[0]['name']
                current['location'] = loc[0]['combined']
            else: # if only arrived or comments are given, use institution as location
                current['location_id'] = current['institution_id']
                current['location_name'] = current['institution_name']
                current['location'] = current['institution']

            if current['arrived'] in (None, ""):
                current['arrived'] = datetime.now().astimezone()
            else:
                arrived = current['arrived']
                iso_arrived = datetime.fromisoformat(arrived)
                if iso_arrived.tzinfo is None:
                    iso_arrived = datetime.fromisoformat(arrived).astimezone()
                current['arrived'] = iso_arrived.isoformat() 
 
        elif not self.is_new():
            current["location_id"] = last_commit['location_id']
            current["location_name"] = last_commit['location_name']
            current["location"] = last_commit['location']
            current["arrived"] = last_commit['arrived']
            current["location_comments"] = last_commit["location_comments"]


        # Normalize COUNTRY
        # if there's no country, default to the institution's country
        if current["country"] or current["country_name"] or current["country_code"]:
            countries = ut.lookup_country(
                    country_code=current["country_code"],
                    country_name=current["country_name"],
                    country=current["country"])
            if len(countries) == 1:
                current["country_code"] = countries[0]['code']
                current["country_name"] = countries[0]['name']
                current["country"] = countries[0]['combined'] 
            else:
                valid = False
        elif not self.is_new():
            current["country_code"] = last_commit['country_code']
            current["country_name"] = last_commit['country_name']
            current["country"] = last_commit['country']
        else:
            # we can assume that 'inst' has been assigned because we would
            # already have thrown an exception if this was a new item that
            # didn't have an institution.
            current["country_code"] = inst[0]['country']['code']
            current["country_name"] = inst[0]['country']['name']
            current["country"] = inst[0]['country']['combined']

        # Normalize MANUFACTURER
        if current['manufacturer_id'] or current['manufacturer_name'] or current['manufacturer']:
            manu = ut.lookup_manufacturer(
                    manufacturer_id=current['manufacturer_id'],
                    manufacturer_name=current['manufacturer_name'],
                    manufacturer=current['manufacturer'])
            if len(manu) == 0:
                msg = ("No manufacturers match the criteria given: "
                        f"ID: {current['manufacturer_id']}, "
                        f"Name: {current['manufacturer_name']}, "
                        f"Repr: {current['manufacturer']}")
                logger.error(msg)
                raise ra.NotFound(msg)
            elif len(manu) == 1:
                current['manufacturer_id'] = manu[0]['id']
                current['manufacturer_name'] = manu[0]['name']
                current['manufacturer'] = manu[0]['combined']
            else:
                msg = ("The fields for Manufacturer do not uniquely identify a "
                        "single manufacturer: "
                        f"ID: {current['manufacturer_id']}, "
                        f"Name: {current['manufacturer_name']}, "
                        f"Repr: {current['manufacturer']}")
                logger.error(msg)
                raise ra.AmbiguousParameters(msg)
        elif not self.is_new():
            current['manufacturer_id'] = last_commit['manufacturer_id'] 
            current['manufacturer_name'] = last_commit['manufacturer_name']
            current['manufacturer'] = last_commit['manufacturer'] 
        else:
            # Not a problem because Manufacturer is optional
            pass

        # Normalize SERIAL NUMBER
        if not self.is_new() and current['serial_number'] is None:
            current['serial_number'] = last_commit['serial_number']
        #if current['serial_number'] == "<null>":
        #    current['serial_number'] = None
        current['serial_number'] = literal_null_check(current['serial_number'])

        # Normalize COMMENTS
        if not self.is_new() and current['comments'] is None:
            current['comments'] = last_commit['comments']
        #if current['comments'] == '<null>':
        #    current['comments'] = None
        current['comments'] = literal_null_check(current['comments'])

        # Normalize SUBCOMPONENTS
        if not self.is_new():
            for k, v in current["subcomponents"].items():
                if v is None:
                    current['subcomponents'][k] = last_commit['subcomponents'].get(k, None)
                #if v == "<null>":
                #    current["subcomponents"][k] = None
                current['subcomponents'][k] = literal_null_check(current['subcomponents'][k])
        else:
            if current["subcomponents"] is not None:
                for k, v in current["subcomponents"].items():
                    current['subcomponents'][k] = literal_null_check(current['subcomponents'][k])

        # Normalize SPECIFICATIONS
        if not self.is_new():
            for k, v in current["specifications"].items():
                if v is None:
                    current['specifications'][k] = last_commit['specifications'].get(k, None)
                #if v == "<null>":
                #    current["specifications"][k] = None
                current['specifications'][k] = literal_null_check(current['specifications'][k])
                #logger.warning(f"{k}: {current['specifications'][k]}")
        
        # Normalize STATUS
        #print(json.dumps(current, indent=4))
        #print(json.dumps(last_commit, indent=4))
        if not self.is_new() and current['status'] is None:
            current['status'] = last_commit['status']
        if current['status'] in ('<null>', '<empty>', '<nan>'):
            current['status'] = 1
        elif isinstance(current['status'], str):
            stat_str = current['status'].casefold()
            if stat_str in ['available', '1']: 
                current['status'] = 1
            elif stat_str in ['unavailable', 'not available', '2']:
                current['status'] = 2
            elif stat_str in ['defunct', 'permanently not available', '3']:
                current['status'] = 3
            else:
                logger.warning(f"Status string '{stat_str}' is not valid. This will likely fail "
                        "when updating the HWDB.")

        #}}}

    #--------------------------------------------------------------------------

    def validate(self):
        """Tests whether this HWItem appears to be valid

        Checks that all required 'core' data exists and appears to meet
        requirements in the ComponentType definition.
        """
        #Style.notice.print(json.dumps(self._part_type, indent=4))

        # Check user role
        if not ut.user_role_check(self.part_type_id):
            raise ra.InsufficientPermissions("The user is not authorized to "
                    f"modify records of type '{self.part_type_id}'")


        # Check manufacturer
        available_manufacturer_ids = {
                m['id'] for m in self._part_type["ComponentType"]["manufacturers"]}

        if self.manufacturer_id is not None \
                and self.manufacturer_id not in available_manufacturer_ids:
            raise ValueError(f"Manufacturer '{self.manufacturer}' is not available for "
                    "component type '{self.part_type_id}'")


        # Check spec fields
        spec_def_keys = {k: None for k in self._part_type["ComponentType"]["properties"]
                                    ["specifications"][-1]["datasheet"].keys()}
        spec_keys = {k: None for k in self.specifications.keys()}
        # (compare them WITHOUT the _meta field for now, but resolve it later)
        spec_def_keys.pop("_meta", None)
        spec_keys.pop("_meta", None)
        if spec_def_keys != spec_keys:
            raise ValueError(f"The specifications for this item do not meet the "
                    "requirements in the specification definition")


    #--------------------------------------------------------------------------


    def update(self):
        """Update the 'core' properties, 'enabled', and subcomponents"""
    
    #--------------------------------------------------------------------------

    def resync(self):
        """Download this HWItem from the HWDB and overwrite current properties"""
        # TODO: maybe I don't need this at all

    #--------------------------------------------------------------------------

    def verify(self):
        """Download this HWItem from the HWDB and check for equivalence"""
        # TODO: maybe I don't need this at all

    #--------------------------------------------------------------------------

    def core_has_changed(self):
        """Tell whether the 'core' properties have changed since downloading"""
    
        if self.is_new():
            return True

        current = self._current
        last_commit = self._last_commit

        if current['serial_number'] != last_commit['serial_number']:
            return True
        if current['manufacturer'] != last_commit['manufacturer']:
            return True
        if current['comments'] != last_commit['comments']:
            return True
        if current['specifications'] != last_commit['specifications']:
            return True
        #if current['enabled'] != last_commit['enabled']:
        #    return True

        return False



    #--------------------------------------------------------------------------

    def enabled_has_changed(self):
        """Tell whether the 'enabled' property has changed since downloading"""
        
        current = self._current
        last_commit = self._last_commit
    
        if self.is_new():
            # The default should be 1, so return True if it's set to anything else
            return current['status'] != 1

        if current['status'] != last_commit['status']:
            return True

        return False

    #--------------------------------------------------------------------------

    def subcomponents_have_changed(self):
        """Tell whether the subcomponents have changed since downloading"""
        
        current = self._current
        last_commit = self._last_commit
    
        if self.is_new():
            return any(current['subcomponents'].values())
        
        if current['subcomponents'] != last_commit['subcomponents']:
            return True

        return False


    #--------------------------------------------------------------------------

    def has_changed(self):
        """Tell whether anything has changed since downloading"""
    
        return any([
            self.core_has_changed(), 
            self.enabled_has_changed(), 
            self.subcomponents_have_changed()])

    #--------------------------------------------------------------------------


    def __str__(self):
        #{{{
        style_bold = Style.bold()
        style_green = Style.fg(0x33ff33).bold()
        style_yellow = Style.fg(0xdddd22).bold()

        fp = io.StringIO()


        def display_new_item():
            #fp.write(style_green("ADD NEW ITEM"))
            #fp.write("\n")
            #table_data = [
            #    ['Property', 'Value']

            #]

            #table = Table(table_data)
            #table.set_row_border(1, BoxDraw.BORDER_STRONG)
            #table.set_column_border(1, BoxDraw.BORDER_STRONG)
            
            #fp.write(table.generate())
            
            current = self._current

            header_data = [
                ["Operation", style_green("CREATE NEW ITEM")],
                ["Part Type ID", current['part_type_id']],
                ["Part Type Name", current['part_type_name']],
            ]
            
            header_table = Table(header_data)
            header_table.set_column_width(0, 15)
            header_table.set_column_width(1, 61)
            fp.write(header_table.generate())
            fp.write("\n")

            table_data = [
                [ style_bold(s) for s in 
                    ['Property',        'Value'] ],
                ['External ID',     current['part_id']],
                ['Institution',     current['institution']],
                ['Country',         current['country']],

                ['Serial Number', current['serial_number']],
                ['Manufacturer', current['manufacturer']],
                ['Comments', current['comments']],
            
                [ 'Subcomponents',
                  json.dumps(current['subcomponents'], indent=4)],

                [ 'Specifications',
                  json.dumps(current['specifications'], indent=4)],
                ['Location', current['location']],           
 
                ['Status', current['status']],
            ]
            table = Table(table_data)
            table.set_row_border(1, BoxDraw.BORDER_STRONG)
            table.set_column_border(1, BoxDraw.BORDER_STRONG)
            table.set_column_width(0, 15)
            table.set_column_width(1, 81)
 
            #fp.write(table.generate(trunc_char='…'))
            fp.write(table.generate(trunc_char='▶', trunc_style=Style.fg(0x8888ff)))



        def display_edited_item():
            current = self._current
            latest = self._last_commit

            header_data = [
                ["Operation", style_yellow("EDIT ITEM")],
                ["Part Type ID", latest['part_type_id']],
                ["Part Type Name", latest['part_type_name']],
            ]            
            header_table = Table(header_data)
            header_table.set_column_width(0, 15)
            header_table.set_column_width(1, 61)
            fp.write(header_table.generate())
            fp.write("\n")
            label_fixed = Style.fg(0x777777).italic()("(fixed)")
            table_data = [
                [ style_bold(s) for s in 
                    ['Property',        'Current Value',            'New Value'] ],
                ['External ID',     latest['part_id'],          label_fixed],
                ['Institution',     latest['institution'],      label_fixed],
                ['Country',         latest['country'],          label_fixed],
            ]

            def add_row(field_name, last_val, current_val):
                row = [ field_name, last_val ]
                if last_val == current_val:
                    row.append(current_val)
                else:
                    stylized = '\n'.join([style_green(line) for line in str(current_val).split('\n')])
                    row.append(stylized)
                    #row.append(Style.fg(0x55ff55)(current_val))
                return row

            table_data.append(add_row('Serial Number', latest['serial_number'], current['serial_number']))
            table_data.append(add_row('Manufacturer', latest['manufacturer'], current['manufacturer']))
            table_data.append(add_row('Comments', latest['comments'], current['comments']))
            
            table_data.append(add_row('Subcomponents',
                    json.dumps(latest['subcomponents'], indent=4),
                    json.dumps(current['subcomponents'], indent=4)))

            table_data.append(add_row('Specifications',
                    json.dumps(restore_order(latest['specifications']), indent=4),
                    json.dumps(restore_order(current['specifications']), indent=4)))
            
            #table_data.append(add_row('Enabled', latest['enabled'], current['enabled']))
            
            table_data.append(add_row("Location", latest['location'], current['location']))
            table_data.append(add_row("Location Comments", latest['location_comments'],
                                         current['location_comments']))
            table_data.append(add_row("Arrived", latest['arrived'], current['arrived']))

            table_data.append(add_row('Status', latest['status'], current['status']))

            table = Table(table_data)
            table.set_row_border(1, BoxDraw.BORDER_STRONG)
            table.set_column_border(1, BoxDraw.BORDER_STRONG)
            table.set_column_width(0, 15)
            table.set_column_width(1, 40)
            table.set_column_width(2, 40)           
 
            #fp.write(table.generate(trunc_char='…'))
            fp.write(table.generate(trunc_char='▶', trunc_style=Style.fg(0x8888ff)))

        if self.is_new():
            display_new_item()
        else:
            display_edited_item()

        return fp.getvalue()
        #}}}

    @staticmethod
    def _is_unassigned(part_id):
        unassigned = (None, '', '<unassigned>', '<null>')
        return (part_id is None) or (part_id.casefold() in unassigned)


    #}}}

if __name__ == "__main__":
    pass






















