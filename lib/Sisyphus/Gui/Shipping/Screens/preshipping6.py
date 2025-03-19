#!/usr/bin/env python

#{{{
from Sisyphus.Configuration import config, USER_SETTINGS_DIR
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut

from Sisyphus.Utils.Terminal.Style import Style

from Sisyphus.Gui.Shipping.Widgets import PageWidget
from Sisyphus.Gui.Shipping.Widgets import ZLineEdit, ZTextEdit, ZCheckBox

from Sisyphus.Gui.Shipping.ShippingLabel import ShippingLabel

from PyQt5.QtCore import QSize, Qt, pyqtSignal, pyqtSlot, QUrl
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QStackedLayout,
    QLabel,
    QTextEdit,
    QPlainTextEdit,
    QLineEdit,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QCheckBox,
    QTabWidget,
    QMenu,
    QMenuBar,
    QAction,
    QStackedWidget,
    QRadioButton,
    QGroupBox,
    QButtonGroup,
)
from PyQt5.QtWebEngineWidgets import QWebEngineView

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib import units
    _reportlab_available = True

except ModuleNotFoundError:
    _reportlab_available = False
import PIL.Image
import io
import smtplib, csv
import tempfile
import json
import os
import base64
#}}}

class PreShipping6(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.pdf_filename = None        
        self.pdf_full_filename = None        

        self.page_message = QLabel('<empty>')
        self.page_message.setWordWrap(True)
        self.pdf_view = QWebEngineView()

        self._construct_page()

    def _construct_page(self):
        screen_layout = QVBoxLayout()
        ########################################

        page_title = QLabel("Pre-Shipping Workflow (6)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        ################

        #screen_layout.addWidget(QLabel("(show shipping sheet)"))
        #screen_layout.addWidget(self.pdf_view)
        screen_layout.addWidget(self.page_message)

        ################
        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)

        #self.generate_shipping_sheet()

    def restore(self):
        super().restore()
        self.generate_shipping_sheet()

    def generate_shipping_sheet(self):

        self.pdf_filename = f"{self.tab_state['part_id']}-shipping-label.pdf"
        self.pdf_full_filename = os.path.realpath(self.pdf_filename)

        ShippingLabel(self.pdf_filename, self.tab_state, show_logo=False, debug=False)


        text = (
            f'''A shipping label has been created at:\n{self.pdf_full_filename}.\n\n'''
            '''Click 'Continue' to update the HWDB.'''
        )

        self.page_message.setText(text)

        #self.pdf_view.load(QUrl.fromLocalFile(filename))
        #self.pdf_view.load(QUrl("https://google.com"))
        #self.pdf_view.show()


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

        specs.setdefault('DATA', {})['Pre-Shipping Checklist'] = \
                    [ {k: v} for k, v in ps_checklist.items() ]
        specs['DATA']['SubPIDs'] = sub_pids

        update_data = {
            "part_id": part_id,
            "comments": item_resp['Item']['comments'],
            "manufacturer": {"id": item_resp['Item']['manufacturer']['id']},
            "serial_number": item_resp['Item']['serial_number'],
            "specifications": specs
        }

        logger.info(json.dumps(update_data, indent=4))
        resp = ra.patch_hwitem(part_id, update_data)
        logger.info(json.dumps(resp, indent=4))




    def on_navigate_next(self):
        super().on_navigate_next()

        self.update_hwdb()        

    #}}}
