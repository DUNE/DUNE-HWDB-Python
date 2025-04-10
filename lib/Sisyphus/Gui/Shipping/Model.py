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

NUM_THREADS = 50
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS)

HLD = highlight = "[bg=#999999,fg=#ffffff]"
HLI = highlight = "[bg=#009900,fg=#ffffff]"
HLW = highlight = "[bg=#999900,fg=#ffffff]"
HLE = highlight = "[bg=#990000,fg=#ffffff]"

###############################################################################

def download_part_info(part_id, status_callback=None):
    #{{{

    fwd_kwargs = {'status_callback': status_callback} if status_callback is not None else {}

    workflow_state = {}

    try:
        hwitem = dm.HWItem(part_id=part_id, **fwd_kwargs)
        #print(hwitem)

        #item_resp = ut.fetch_hwitems(part_id=part_id)[part_id]

        #item_info = item_resp['Item']
        item_info = hwitem.data

        part_type_id = item_info['component_type']['part_type_id']
        part_type_name = item_info['component_type']['name']

        #project_id, system_id, subsystem_id = (
        #                part_type_id[:1], part_type_id[1:4], part_type_id[4:7])


        #sys_info = ra.get_system(project_id, system_id)['data']

        #subsys_info = ra.get_subsystem(project_id, system_id, subsystem_id)['data']

        #resp_qr = ra.get_hwitem_qrcode(part_id=part_id).content
        #part_qr = base64.b85encode(resp_qr).decode('utf-8')

    except (ra.DatabaseError, ValueError) as exc:
        logger.error(f"{HLE}exc")
        return None
    
        msg = f'''<div style="color: #990000">{part_id} not found!</div>'''
        self.pid_search_result_label.setText(msg)

        self.workflow_state['part_info'] = None

        self.update()
        return

    #system_name = sys_info['name']
    #subsystem_name = subsys_info['subsystem_name']
    #system_name = hwitem.system.system
    #subsystem_name = hwitem.subsystem.subsystem

    part_info = {
        "part_id": part_id,
        "part_type_id": part_type_id,
        "part_type_name": part_type_name,
        'system_id': hwitem.system.system_id,
        'system_name': hwitem.system.system_name,
        'subsystem_id': hwitem.subsystem.subsystem_id,
        'subsystem_name': hwitem.subsystem.subsystem_name,
        'qr_code': hwitem.qr_code,
        'subcomponents': {}
    }

    # Set Subcomponents in tab state
    #subcomponent_info = item_resp['Subcomponents']
    subcomponent_info = hwitem.subcomponents
    for subcomp in subcomponent_info:
        part_info['subcomponents'][subcomp['part_id']] = {
            "Sub-component PID": subcomp['part_id'],
            "Component Type Name": subcomp['type_name'],
            "Functional Position Name": subcomp["functional_position"]
        }

    workflow_state['part_info'] = part_info


                


    ###########################
    #
    # Populate pre-shipping
    #
    ###########################
   
    spec = item_info['specifications'][0]
    if type(spec.get("DATA")) is not dict:
        psc = {}
    else:
        data_node = spec.get("DATA", {})
        psc_raw = data_node.get('Pre-Shipping Checklist', [])
        psc = preshipping_checklist = {k:v for d in 
                            psc_raw for k, v in d.items()}

    preshipping_exists = (len(psc) > 0)

    # If there is a record for pre-shipping, we can assume that all the required
    # checkboxes were checked.
    
    workflow_state["PreShipping1"] = {
            "confirm_list": preshipping_exists,
            "hwdb_updated": preshipping_exists,
        }


    workflow_state["PreShipping2"] = {
            "approver_name": psc.get("POC name", ""),
            "approver_email": ', '.join(psc.get("POC Email", [])),
            "test_info": psc.get("QA/QC related info Line 1", ""),
        }
        #"approver_name": "FD Logistics team acknoledgement (name)",
        #"approver_email": 
    
    workflow_state["PreShipping3a"] = {
            "hts_code": psc.get("HTS code", ""),
            "shipment_origin": psc.get("Origin of this shipment", ""),
            "dimension": psc.get("Dimension of this shipment",""),
            "weight": psc.get("Weight of this shipment", ""),
            "shipping_service_type": "Domestic" if psc.get("HTS code", None) is None 
                                                else "International",
        }

    workflow_state["PreShipping3b"] = {
            "freight_forwarder": psc.get("Freight Forwarder name", ""),
            "mode_of_transportation": psc.get("Mode of Transportation", ""),
            "expected_arrival_time": psc.get("Expected Arrival Date (CT)", ""),
        }

    workflow_state["PreShipping4"] = {
            "email_contents": "",
            "confirm_email_contents": preshipping_exists
        }

    workflow_state["PreShipping5"] = {
            "received_acknowledgement": preshipping_exists,
            "acknowledged_by": psc.get("FD Logistics team acknoledgement (name)", ""),
            "acknowledged_time": psc.get("FD Logistics team acknoledgement (date in CT)", ""),
            "damage_status": "no damage" 
                                if psc.get("Visual Inspection (YES = no damage)", None) == "YES"
                                else "damage",
            "damage_description": psc.get("Visual Inspection Damage", ""),
        }


    #print(json.dumps(preshipping_checklist, indent=4))

    #print(json.dumps(workflow_state, indent=4))

    return workflow_state
    #}}}

def upload_shipping(workflow_state):
    #{{{

    ws = workflow_state
    part_id = ws['part_info']['part_id']

    shipping_checklist = {
        "POC name":  ws['SelectPID']['user_name'],
        "POC Email": [s.strip() for s in ws['SelectPID']['user_email'].split(',')],
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

    print(json.dumps(shipping_checklist, indent=4))

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

def populate_preshipping_from_hwdb(part_id):
    ...

def populate_shipping_from_hwdb(part_id):
    ...


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

    return True
    #}}}
