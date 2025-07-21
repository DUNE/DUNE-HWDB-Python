#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2025 Regents of the University of Minnesota
Author:
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)  

from Sisyphus.Gui.Shipping import Widgets as zw
from Sisyphus.Gui.Shipping.Widgets.PageWidget import PageWidget
from Sisyphus.Gui.Shipping.Tasks import Database as dbt

from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

from datetime import datetime

###############################################################################

class Shipping2(PageWidget):
    page_name = "Shipping Workflow (2)"
    page_short_name = "Shipping (2)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bol_file = zw.ZFileSelectWidget(page=self, key='bol_filename')

        self.proforma_container = qtw.QWidget()
        self.proforma_file = zw.ZFileSelectWidget(page=self, key='proforma_filename')

        self._setup_UI()
        #self.refresh()

    def _setup_UI(self):
        #{{{
        main_layout = qtw.QVBoxLayout()

        main_layout.addWidget(self.title_bar)
        #############################



        #main_layout.addWidget(
        #        qtw.QLabel("Select Bill of Lading image file:"))
        
        Departmess = qtw.QLabel("If it is your shipping department who interacts with the Freight Forwarder office on behalf of you, " \
        "make sure to make them to follow the procedure below.")
        Departmess.setWordWrap(True)
        #Departmess.setStyleSheet("""
        #        font-size: 14pt;
        #    """)
        main_layout.addWidget(Departmess)

        BoLTypemess = qtw.QLabel("For this Bill of Lading (BoL), request your carrier to employ a BoL type,"\
        "\"Through Seaway BoL\" or \"Through BoL with an express release\".")
        BoLTypemess.setWordWrap(True)
        #BoLTypemess.setStyleSheet("""
        #        font-size: 14pt;
        #    """)
        main_layout.addWidget(BoLTypemess)

        BoLRequestmess = qtw.QLabel("- Request your carrier to include the shipment PID and its Component Type Name in its BoL.\n" \
        "- Request them to send you the finalized BoL electronically. The image type must be jpg, png, or pdf.")
        BoLRequestmess.setWordWrap(True)
        #BoLRequestmess.setStyleSheet("""
        #        font-size: 14pt;
        #    """)
        main_layout.addWidget(BoLRequestmess)

        SelectBoLmess = qtw.QLabel("Select Bill of Lading image file:")
        SelectBoLmess.setWordWrap(True)
        #SelectBoLmess.setStyleSheet("""
        #        font-size: 14pt;
        #    """)
        main_layout.addWidget(SelectBoLmess)

        main_layout.addWidget(self.bol_file)
       
        main_layout.addSpacing(20)
 

        proforma_layout = qtw.QVBoxLayout()
        proforma_layout.setContentsMargins(0, 0, 0, 0)

        proforma_layout.addSpacing(20)
        Proformamess = qtw.QLabel("- For an international shipment, a Proforma Invoice (i.e., commercial invoice) is " \
        "required additionally.\n- Again, make sure to request your carrier to include the shipment PID and its Component " \
        "Type Name in the invoice.\n- Request them to send you the finalized invoice electronically. " \
        "The image type must be jpg, png, or pdf.")
        Proformamess.setWordWrap(True)
        #Proformamess.setStyleSheet("""
        #        font-size: 14pt;
        #    """)
        proforma_layout.addWidget(Proformamess)

        self.proforma_container.setLayout(proforma_layout)
        main_layout.addWidget(self.proforma_container)

        #main_layout.addWidget(
        #        QLabel("Select Proforma image file:"))
        #main_layout.addWidget(self.proforma_file)
        proforma_layout.addWidget(
                qtw.QLabel("Select Proforma image file:"))
        proforma_layout.addWidget(self.proforma_file)


        main_layout.addSpacing(40)

        self.upload_message = qtw.QLabel(f"Click 'Continue' to upload the selected shipping documentation(s)"\
                                         f" to the HWDB.")
        self.upload_message.setWordWrap(True)
        #self.upload_message.setStyleSheet("""
        #        font-size: 14pt;
        #    """)
        main_layout.addWidget(self.upload_message)



        #############################
        main_layout.addStretch()
        main_layout.addWidget(self.nav_bar)
        self.setLayout(main_layout)
        #}}}

    def select_bol_dialog(self):
        file_dialog = qtw.QFileDialog(self)
        file_dialog.setWindowTitle("Select Bill of Lading Image File")

        if file_dialog.exec():
            self.bol_text.setText(file_dialog.selectedFiles()[0])

    def refresh(self):
        super().refresh()

        shipping_service_type = self.workflow_state.get('PreShipping4a', {}) \
                    .get('shipping_service_type', 'Domestic')

        if shipping_service_type != "International":
            self.proforma_container.setEnabled(False)
            self.page_state['proforma_filename'] = ''
            self.proforma_file.restore()
        else:
            self.proforma_container.setEnabled(True)

        if ( self.page_state.get('bol_filename', '') == ''
                or ( shipping_service_type == 'International' 
                        and self.page_state.get('proforma_filename', '') == '')):
            self.nav_bar.continue_button.setEnabled(False)
        else:
            self.nav_bar.continue_button.setEnabled(True)

    def upload_files(self):
        #{{{
        logger.info(f"{self.__class__.__name__}: uploading files")
        import shutil, os
        
        def rename(filename, prefix):
            username = self.application.whoami['username']
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
            file_ext = filename.split('.')[-1]
            #new_filename = f"{prefix}-{username}-{timestamp}.{file_ext}"
            new_filename = f"{prefix}-{timestamp}.{file_ext}"
            return new_filename

        def upload_file(filename, file_prefix, node_name):
            new_filename = rename(filename, file_prefix)
            new_full_filename = os.path.join(self.workflow.working_directory, new_filename)
            shutil.copy(filename, new_full_filename)

            image_id, checksum = dbt.upload_image(self.part_id, new_full_filename)
            self.page_state[node_name] = {
                "filename": new_filename,
                "image_id": image_id,
                "checksum": checksum
            }
        with self.wait():
            upload_file(self.page_state['bol_filename'], "BoL", "bol_info")

            if self.page_state['proforma_filename']:
                upload_file(self.page_state['proforma_filename'], "ProformaInvoice", "proforma_info")

        return True       
        #}}}

    def on_navigate_next(self):
        #{{{
        ok = super().on_navigate_next()
        if not ok:
            return False

        ok = self.upload_files()
        if not ok:
            return False

        return True
        #}}}
