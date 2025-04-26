#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""
from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut

from Sisyphus.Utils.Terminal.Style import Style

from Sisyphus.Gui import DataModel as dm

import json
import base64, PIL.Image, io
import sys
import re
import functools
import threading
import concurrent.futures
import hashlib

###############################################################################

def download_part_info(part_id, refresh=False, status_callback=None):
    #{{{

    fwd_kwargs = {}
    if status_callback is not None:
        fwd_kwargs['status_callback'] = status_callback
    if refresh:
        fwd_kwargs['refresh'] = True

    workflow_state = {}

    try:
        hwitem = dm.HWItem(part_id=part_id, **fwd_kwargs)
        item_info = hwitem.data

    except (ra.DatabaseError, ValueError) as exc:
        logger.error(f"{type(exc)}:{exc}")
        hwitem = None

    if hwitem:
        part_type_id = item_info['component_type']['part_type_id']
        part_type_name = item_info['component_type']['name']

        part_info = {
            "part_id": part_id,
            "part_type_id": part_type_id,
            "part_type_name": part_type_name,
            'system_id': hwitem.system.system_id,
            'system_name': hwitem.system.system_name,
            'system': f"{hwitem.system.system_name} ({hwitem.system.system_id})",
            'subsystem_id': hwitem.subsystem.subsystem_id,
            'subsystem_name': hwitem.subsystem.subsystem_name,
            'subsystem': f"{hwitem.subsystem.subsystem_name} ({hwitem.subsystem.subsystem_id})",
            'qr_code': hwitem.qr_code,
            'connectors': hwitem.component_type.data['connectors'],
            'subcomponents': {}
        }

        connector_data = {}
        for k, v in hwitem.component_type.data['connectors'].items():
            subcomp_type = dm.ComponentType(part_type_id=v).data
            subcomp_type_name = subcomp_type['full_name'].split('.')[-1]
            connector_data[k] = {
                "part_type_id": v,
                "part_type_name": subcomp_type_name
            }
        part_info['connector_data'] = connector_data

        # Set Subcomponents in tab state
        subcomponent_info = hwitem.subcomponents
        for subcomp in subcomponent_info:
            part_info['subcomponents'][subcomp['part_id']] = {
                "Sub-component PID": subcomp['part_id'],
                "Component Type Name": subcomp['type_name'],
                "Functional Position Name": subcomp["functional_position"]
            }

        workflow_state['part_info'] = part_info
        spec = item_info['specifications'][0]
    else:
        workflow_state['part_info'] = {}
        spec = {}

    workflow_state.update(populate_preshipping_from_hwdb(spec))
    workflow_state.update(populate_shipping_from_hwdb(spec))

    return workflow_state

def populate_preshipping_from_hwdb(spec):
    workflow_state = {}
   
    if type(spec.get("DATA")) is not dict:
        psc = {}
    else:
        data_node = spec.get("DATA", {})
        psc_raw = data_node.get('Pre-Shipping Checklist', [])
        if type(psc_raw) is list:
            psc = preshipping_checklist = {k:v for d in 
                                psc_raw for k, v in d.items()}
        else:
            psc = psc_raw

    preshipping_exists = (len(psc) > 0)

    # If there is a record for pre-shipping, we can assume that all the required
    # checkboxes were checked.
    
    workflow_state["PreShipping1"] = {
            "confirm_list": preshipping_exists,
            "hwdb_updated": preshipping_exists,
        }

    workflow_state["PreShipping2"] = {
            "qa_rep_name": psc.get("QA Rep name", ""),
            "qa_rep_email": ', '.join(psc.get("QA Rep Email", [])),
            "test_info": psc.get("QA/QC related info Line 1", ""),
        }

    workflow_state["PreShipping3"] = {
            "approver_name": psc.get("POC name", ""),
            "approver_email": ', '.join(psc.get("POC Email", [])),
        }
    
    workflow_state["PreShipping4a"] = {
            "hts_code": psc.get("HTS code", ""),
            "shipment_origin": psc.get("Origin of this shipment", ""),
            "dimension": psc.get("Dimension of this shipment",""),
            "weight": psc.get("Weight of this shipment", ""),
            "shipping_service_type": "Domestic" if psc.get("HTS code", None) is None 
                                                else "International",
        }

    workflow_state["PreShipping4b"] = {
            "freight_forwarder": psc.get("Freight Forwarder name", ""),
            "mode_of_transportation": psc.get("Mode of Transportation", ""),
            "expected_arrival_time": psc.get("Expected Arrival Date (CT)", ""),
        }

    workflow_state["PreShipping5"] = {
            "email_contents": "",
            "confirm_email_contents": preshipping_exists
        }

    workflow_state["PreShipping6"] = {
            "received_acknowledgement": preshipping_exists,
            "acknowledged_by": psc.get("FD Logistics team acknoledgement (name)", ""),
            "acknowledged_time": psc.get("FD Logistics team acknoledgement (date in CT)", ""),
            "damage_status": "no damage" 
                                if psc.get("Visual Inspection (YES = no damage)", None) == "YES"
                                else "damage",
            "damage_description": psc.get("Visual Inspection Damage", ""),
        }

    return workflow_state
    #}}}

def populate_shipping_from_hwdb(part_id):
    workflow_state = {}

    #TODO: populate shipping

    return workflow_state


def upload_shipping(workflow_state):
    #{{{

    ws = workflow_state
    part_id = ws['part_info']['part_id']

    shipping_checklist = {
        "POC name":  ws['PreShipping3']['approver_name'],
        "POC Email": [s.strip() for s in ws['PreShipping3']['approver_email'].split(',')],
        "System Name (ID)": f"{ws['part_info']['system_name']}"
                               f" ({ws['part_info']['system_id']})",
        "Subsystem Name (ID)":  f"{ws['part_info']['subsystem_name']}"
                               f" ({ws['part_info']['subsystem_id']})",
        "Component Type Name (ID)":  f"{ws['part_info']['part_type_name']}"
                                f" ({ws['part_info']['part_type_id']})",
        "DUNE PID": part_id,
        "Image ID for BoL": ws['Shipping2']['bol_info']['image_id'],
        "Image ID for Proforma Invoice": ws['Shipping2'].get('proforma_info', {}).get('image_id', None),
        "Image ID for the final approval message": ws['Shipping4']['approval_info']['image_id'],
        "FD Logistics team final approval (name)": ws['Shipping4']['approved_by'],
        "FD Logistics team final approval (date in CST)": ws['Shipping4']['approved_time'],
        "DUNE Shipping Sheet has been attached": ws['Shipping4']['confirm_attached_sheet'],
        "This shipment has been adequately insured for transit": ws['Shipping4']['confirm_insured']
    }

    #print(json.dumps(shipping_checklist, indent=4))

    # Get the current specifications and add to it
    item_resp = ut.fetch_hwitems(part_id=part_id)[part_id]
    logger.info(json.dumps(item_resp, indent=4))
    specs = item_resp['Item']['specifications'][-1]

    # Sometimes this bastard 'DATA' is a list instead of a dict!
    # So wipe it out and make it a dict.
    if not isinstance(specs.get('DATA'), dict):
        specs['DATA'] = {}

    specs['DATA']['Shipping Checklist'] = \
                [ {k: v} for k, v in shipping_checklist.items() ]

    if item_resp['Item']['manufacturer'] is not None:
        manufacturer_node = {"id": item_resp['Item']['manufacturer']['id']}
    else:
        manufacturer_node = None

    update_data = {
        "part_id": part_id,
        "comments": item_resp['Item']['comments'],
        "manufacturer": manufacturer_node,
        "serial_number": item_resp['Item']['serial_number'],
        "specifications": specs
    }

    logger.info(json.dumps(update_data, indent=4))
    resp = ra.patch_hwitem(part_id, update_data)
    logger.info(json.dumps(resp, indent=4))

    return True
    #}}}



def upload_image(part_id, filename):
    #{{{
    checksum = hashlib.md5(open(filename, 'rb').read()).hexdigest()

    data = {
        "comments": checksum
    }

    image_id = ra.post_hwitem_image(part_id, data, filename)['image_id']
    return image_id, checksum
    #}}}

def update_location(part_id, location, arrived, comments):
    #{{{

    data = {
        "location":
        {
            "id": location,
        },
        "arrived": arrived,
        "comments": comments,
    }

    resp = ra.post_hwitem_location(part_id, data)
    return True
    #}}}

def update_locations_and_detach(part_id, location, arrived, comments):
    #{{{

    update_location(part_id, location, arrived, comments)

    hwitem = dm.HWItem(part_id=part_id)
    

    for subcomponent in hwitem.subcomponents:
        update_location(subcomponent['part_id'], location, arrived, comments)

    payload = {
        "component": {"part_id": part_id},
        "subcomponents": {s['functional_position']: None for s in hwitem.subcomponents},
    }
    
    resp = ra.patch_subcomponents(part_id, payload)

    # Refresh the cache
    hwitem = dm.HWItem(part_id=part_id, refresh=True)

    return True
    #}}}
