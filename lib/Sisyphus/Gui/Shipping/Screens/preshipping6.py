#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

HLD = highlight = "[bg=#999999,fg=#ffffff]"
HLI = highlight = "[bg=#009900,fg=#ffffff]"
HLW = highlight = "[bg=#999900,fg=#ffffff]"
HLE = highlight = "[bg=#990000,fg=#ffffff]"

from Sisyphus.Utils.Terminal.Style import Style
from Sisyphus.Gui.Shipping import Widgets as zw
from Sisyphus.Gui.Shipping import Model as mdl
from Sisyphus.Gui.Shipping.ShippingLabel import ShippingLabel

from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut

from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
#from PyQt5 import QtWebEngineWidgets as qtweb

import os
import json


class PreShipping6(zw.PageWidget):
    page_name = "Pre-Shipping Workflow (6)"
    page_short_name = "Pre-Shipping (6)"

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
        ########################################

        #page_title = qtw.QLabel("Pre-Shipping Workflow (6)")
        #page_title.setStyleSheet("""
        #        font-size: 14pt;
        #        font-weight: bold;
        #    """)
        #page_title.setAlignment(qtc.Qt.AlignCenter)
        #main_layout.addWidget(page_title)
        main_layout.addWidget(self.title_bar)
        ################

        main_layout.addWidget(self.page_message)

        ################
        main_layout.addStretch()

        main_layout.addWidget(self.nav_bar)

        self.setLayout(main_layout)

        #self.generate_shipping_sheet()

    def restore(self):
        super().restore()
        self.generate_shipping_sheet()

    def generate_shipping_sheet(self):
        self.pdf_filename = f"{self.tab_state['part_info']['part_id']}-shipping-label.pdf"
        self.pdf_full_filename = os.path.join(self.working_directory, self.pdf_filename)

        ShippingLabel(self.pdf_full_filename, self.tab_state, show_logo=False, debug=False)


        text = (
            f'''A shipping label has been created at:\n{self.pdf_full_filename}.\n\n'''
            '''Click 'Continue' to update the HWDB.'''
        )

        self.page_message.setText(text)


    def update_hwdb(self):
        if self.pdf_full_filename is None:
            self.generate_shipping_sheet()

        print(self.pdf_full_filename)

        ts = self.tab_state
        part_id = ts['part_info']['part_id']

        #####
        # post the image first...
        data = {
            "comments": f"shipping sheet",
        }

        resp = ra.post_hwitem_image(part_id, data, self.pdf_full_filename)
        image_id = resp['image_id']


        ps_checklist = {
            "POC name": ts['SelectPID']['user_name'],
            "POC Email": [s.strip() for s in ts['SelectPID']['user_email'].split(',')],
            "System Name (ID)": f"{ts['part_info']['system_name']}"
                               f" ({ts['part_info']['system_id']})",
            "Subsystem Name (ID)":  f"{ts['part_info']['subsystem_name']}"
                               f" ({ts['part_info']['subsystem_id']})",
            "Component Type Name (ID)": f"{ts['part_info']['part_type_name']}"
                                f" ({ts['part_info']['part_type_id']})",
            "DUNE PID": part_id,
            "QA/QC related info Line 1": ts['PreShipping2']['test_info'],
            "HTS code": ts['PreShipping3a']['hts_code'] 
                               if ts['PreShipping3a']['shipping_service_type'] 
                                    != 'Domestic' else None ,
            "Origin of this shipment": ts['PreShipping3a']['shipment_origin'],
            "Dimension of this shipment": ts['PreShipping3a']['dimension'],
            "Weight of this shipment": ts['PreShipping3a']['weight'],
            "Freight Forwarder name": ts['PreShipping3b']['freight_forwarder'],
            "Mode of Transportation": ts['PreShipping3b']['mode_of_transportation'],
            "Expected Arrival Date (CT)": ts['PreShipping3b']['expected_arrival_time'],
            "FD Logistics team acknoledgement (name)": ts['PreShipping5']['acknowledged_by'],
            "FD Logistics team acknoledgement (date in CT)": ts['PreShipping5']['acknowledged_time'],
            "Visual Inspection (YES = no damage)": 
                    'YES' if ts['PreShipping5']['damage_status']=='no damage' else 'NO',
            "Visual Inspection Damage": ts['PreShipping5']['damage_description'],
            "Image ID for this Shipping Sheet": image_id
        }

        sub_pids = []
        for k, v in ts['part_info']['subcomponents'].items():
            sub_pids.append({
                f"{v['Component Type Name']} ({v['Functional Position Name']})": 
                        v['Sub-component PID']
            })

        # Get the current specifications and add to it
        item_resp = ut.fetch_hwitems(part_id=part_id)[part_id]
        logger.info(json.dumps(item_resp, indent=4))
        specs = item_resp['Item']['specifications'][-1]

        # Sometimes this bastard 'DATA' is a list instead of a dict!
        # So wipe it out and make it a dict.
        if not isinstance(specs.get('DATA'), dict):
            specs['DATA'] = {}

        specs['DATA']['Pre-Shipping Checklist'] = \
                    [ {k: v} for k, v in ps_checklist.items() ]
        specs['DATA']['SubPIDs'] = sub_pids

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




    def on_navigate_next(self):
        super().on_navigate_next()

        self.update_hwdb()        

