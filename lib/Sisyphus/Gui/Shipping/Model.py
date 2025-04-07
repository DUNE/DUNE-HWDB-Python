#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""
from Sisyphus.Configuration import config, USER_SETTINGS_DIR
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut

from Sisyphus.Utils.Terminal.Style import Style

from Sisyphus.Gui.Shipping import DataModel as dm

import json
import base64, PIL.Image, io
import sys
import re
import functools
import threading
import concurrent.futures
NUM_THREADS = 50
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS)

HLD = highlight = "[bg=#999999,fg=#ffffff]"
HLI = highlight = "[bg=#009900,fg=#ffffff]"
HLW = highlight = "[bg=#999900,fg=#ffffff]"
HLE = highlight = "[bg=#990000,fg=#ffffff]"


#{{{

def download_part_info(part_id, status_callback=None):

    fwd_kwargs = {'status_callback': status_callback} if status_callback is not None else {}

    tab_state = {}

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

        self.tab_state['part_info'] = None

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

    tab_state['part_info'] = part_info


                


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
    
    tab_state["PreShipping1"] = {
            "confirm_list": preshipping_exists,
            "hwdb_updated": preshipping_exists,
        }


    tab_state["PreShipping2"] = {
            "approver_name": psc.get("POC name", ""),
            "approver_email": ', '.join(psc.get("POC Email", [])),
            "test_info": psc.get("QA/QC related info Line 1", ""),
        }
        #"approver_name": "FD Logistics team acknoledgement (name)",
        #"approver_email": 
    
    tab_state["PreShipping3a"] = {
            "hts_code": psc.get("HTS code", ""),
            "shipment_origin": psc.get("Origin of this shipment", ""),
            "dimension": psc.get("Dimension of this shipment",""),
            "weight": psc.get("Weight of this shipment", ""),
            "shipping_service_type": "Domestic" if psc.get("HTS code", None) is None 
                                                else "International",
        }

    tab_state["PreShipping3b"] = {
            "freight_forwarder": psc.get("Freight Forwarder name", ""),
            "mode_of_transportation": psc.get("Mode of Transportation", ""),
            "expected_arrival_time": psc.get("Expected Arrival Date (CT)", ""),
        }

    tab_state["PreShipping4"] = {
            "email_contents": "",
            "confirm_email_contents": preshipping_exists
        }

    tab_state["PreShipping5"] = {
            "received_acknowledgement": preshipping_exists,
            "acknowledged_by": psc.get("FD Logistics team acknoledgement (name)", ""),
            "acknowledged_time": psc.get("FD Logistics team acknoledgement (date in CT)", ""),
            "damage_status": "no damage" 
                                if psc.get("Visual Inspection (YES = no damage)", None) == "YES"
                                else "damage",
            "damage_description": psc.get("Visual Inspection Damage", ""),
        }


    #print(json.dumps(preshipping_checklist, indent=4))

    #print(json.dumps(tab_state, indent=4))

    return tab_state

def upload_shipping(part_id):
    shipping_checklist = {
        "POC name": "Hajime Muramatsu",
        "POC Email": [
            "hmuramat@umn.edu",
            "hajime.muramatsu@gmail.com"
        ],
        "System Name (ID)": "FD1-HD HVS (005)",
        "Subsystem Name (ID)": "HWDBUnitTest (998)",
        "Component Type Name (ID)": "Test Type 007 (D00599800007)",
        "DUNE PID": "D00599800007-00075",
        "Image ID for BoL": "864966a0-d6c0-11ef-94fc-5fad7be5af4a",
        "Image ID for Proforma Invoice": "88024d18-d6c0-11ef-9904-0bc5dd4b6979",
        "Image ID for the final approval message": "93e250ba-d6c0-11ef-a5e4-3349190277b1",
        "FD Logistics team final approval (name)": "Hajime",
        "FD Logistics team final approval (date in CST)": "2025-01-19 17:51:14",
        "DUNE Shipping Sheet has been attached": "YES",
        "This shipment has been adequately insured for transit": "YES",
    }

def populate_preshipping_from_hwdb(part_id):
    ...

def populate_shipping_from_hwdb(part_id):
    ...



#}}}

def main():
    ...

if __name__ == '__main__':
    sys.exit(main())
