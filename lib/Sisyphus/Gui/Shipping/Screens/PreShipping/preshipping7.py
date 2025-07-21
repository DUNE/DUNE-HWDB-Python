#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus.Gui.Shipping import Widgets as zw
from Sisyphus.Gui.Shipping.Widgets.PageWidget import PageWidget
from Sisyphus.Gui.Shipping.Tasks.ShippingLabel import ShippingLabel
from Sisyphus.Gui import DataModel as dm

from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut

from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
#from PyQt5 import QtWebEngineWidgets as qtweb

import os
import json


class PreShipping7(PageWidget):
    page_name = "Pre-Shipping Workflow (7)"
    page_short_name = "Pre-Shipping (7)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.pdf_filename = None        
        self.pdf_full_filename = None        

        self.page_message = qtw.QLabel('<empty>')
        self.page_message.setWordWrap(True)
        #self.pdf_view = qtweb.QWebEngineView()

        self._setup_UI()

    def _setup_UI(self):
        main_layout = qtw.QVBoxLayout()
        main_layout.addWidget(self.title_bar)
        ################

        main_layout.addWidget(self.page_message)

        ################
        main_layout.addStretch()

        main_layout.addWidget(self.nav_bar)

        self.setLayout(main_layout)

    def restore(self):
        super().restore()
        self.generate_shipping_sheet()

    def generate_shipping_sheet(self):
        self.pdf_filename = f"{self.workflow_state['part_info']['part_id']}-shipping-label.pdf"
        self.pdf_full_filename = os.path.join(self.workflow.working_directory, self.pdf_filename)

        ShippingLabel(self.pdf_full_filename, self.workflow_state, show_logo=False, debug=False)


        text = (
            f'''A shipping label has been created at:\n{self.pdf_full_filename}.\n\n'''
            '''Click 'Continue' to update the HWDB.'''
        )

        self.page_message.setText(text)


    def update_hwdb(self):
        if self.pdf_full_filename is None:
            self.generate_shipping_sheet()

        #print(self.pdf_full_filename)

        ws = self.workflow_state
        part_id = ws['part_info']['part_id']

        #####
        # post the image first...
        data = {
            "comments": f"shipping sheet",
        }

        try:
            resp = ra.post_hwitem_image(part_id, data, self.pdf_full_filename)
        except Exception as exc:
            msg = (f"An error occurred in attempting to upload the shipping sheet. "
                    f"part_id: {part_id}, data: {data}, filename: {self.pdf_full_filename}")
            logger.error(msg)
            Style.error.print(msg)
            raise
        image_id = resp['image_id']


        ps_checklist = {
            "QA Rep name": ws['PreShipping2']['qa_rep_name'],
            "QA Rep Email": [s.strip() for s in ws['PreShipping2']['qa_rep_email'].split(',')],
            "POC name": ws['PreShipping3']['approver_name'],
            "POC Email": [s.strip() for s in ws['PreShipping3']['approver_email'].split(',')],
            "System Name (ID)": f"{ws['part_info']['system_name']}"
                               f" ({ws['part_info']['system_id']})",
            "Subsystem Name (ID)":  f"{ws['part_info']['subsystem_name']}"
                               f" ({ws['part_info']['subsystem_id']})",
            "Component Type Name (ID)": f"{ws['part_info']['part_type_name']}"
                                f" ({ws['part_info']['part_type_id']})",
            "DUNE PID": part_id,
            "HTS code": ws['PreShipping4a']['hts_code'] 
                               if ws['PreShipping4a']['shipping_service_type'] 
                                    != 'Domestic' else None ,
            "Origin of this shipment": ws['PreShipping4a']['shipment_origin'],
            "Dimension of this shipment": ws['PreShipping4a']['dimension'],
            "Weight of this shipment": ws['PreShipping4a']['weight'],
            "Freight Forwarder name": ws['PreShipping4b']['freight_forwarder'],
            "Mode of Transportation": ws['PreShipping4b']['mode_of_transportation'],
            "Expected Arrival Date (CT)": ws['PreShipping4b']['expected_arrival_time'],
            "FD Logistics team acknoledgement (name)": ws['PreShipping6']['acknowledged_by'],
            "FD Logistics team acknoledgement (date in CT)": ws['PreShipping6']['acknowledged_time'],
            "Visual Inspection (YES = no damage)": 
                    'YES' if ws['PreShipping6']['damage_status']=='no damage' else 'NO',
            "Visual Inspection Damage": ws['PreShipping6']['damage_description'],
            "Image ID for this Shipping Sheet": image_id
        }

        sub_pids = []
        for k, v in ws['part_info']['subcomponents'].items():
            sub_pids.append({
                f"{v['Component Type Name']} ({v['Functional Position Name']})": 
                        v['Sub-component PID']
            })

        # Get the current specifications and add to it
        #item_resp = ut.fetch_hwitems(part_id=part_id)[part_id]
        item_resp = {'Item': dm.HWItem(part_id=part_id).data}
        logger.info(json.dumps(item_resp, indent=4))
        specs = item_resp['Item']['specifications'][-1]

        # Sometimes this bastard 'DATA' is a list instead of a dict!
        # So wipe it out and make it a dict.
        if not isinstance(specs.get('DATA'), dict):
            specs['DATA'] = {}

        specs['DATA']['Pre-Shipping Checklist'] = \
                    [ {k: v} for k, v in ps_checklist.items() ]
        specs['DATA']['SubPIDs'] = sub_pids

        #if item_resp['Item']['manufacturer'] is not None:
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

        # Refresh the data in the cache
        # Note that we're not extracting the data, so the cache will be 
        # silently refreshed in the background until someone else asks
        # for it. (If it's not done yet, then at that time, it will block
        # until the refresh is complete. But there's no reason to block now.)
        item_future = dm.HWItem(part_id=part_id, refresh=True)



    def on_navigate_next(self):
        super().on_navigate_next()

        with self.wait():
            self.update_hwdb()        

        return True
