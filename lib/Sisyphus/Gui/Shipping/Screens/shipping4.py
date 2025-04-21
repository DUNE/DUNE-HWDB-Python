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

from Sisyphus.Gui.Shipping import Widgets as zw
from Sisyphus.Gui.Shipping import Model as mdl
from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

###############################################################################

class Shipping4(zw.PageWidget):
    page_name = "Shipping Workflow (4)"
    page_short_name = "Shipping (4)"

    def __init__(self, *args, **kwargs):
        #{{{
        super().__init__(*args, **kwargs)

        self.received_approval = zw.ZCheckBox("Yes, I have received an approval",
                    owner=self, key='received_approval')
        self.approved_by = zw.ZLineEdit(owner=self, key='approved_by')
        self.approved_time = zw.ZDateTimeEdit(owner=self, key='approved_time')
        self.approval_image = zw.ZFileSelectWidget(owner=self, key='approved_image')

        msg = "The DUNE Shipping Sheet has been securely attached to the shipment"
        self.confirm_attached_sheet = zw.ZCheckBox(owner=self, text=msg, key="confirm_attached_sheet")

        msg = "The cargo has been adequately insured for transit"
        self.confirm_insured = zw.ZCheckBox(owner=self, text=msg, key="confirm_insured")

        self._setup_UI()
        #}}}

    def _setup_UI(self):
        #{{{
        main_layout = qtw.QVBoxLayout()
        ########################################

        page_title = qtw.QLabel("Shipping Workflow (4)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(qtc.Qt.AlignCenter)
        main_layout.addWidget(page_title)

        ################

        label1 = qtw.QLabel(
                "An email has been sent to the FD Logistics Team. "
                "Do not continue until you have received an approval from them."
        )
        label1.setWordWrap(True)
        main_layout.addWidget(label1)
        main_layout.addSpacing(15)


        main_layout.addWidget(
            qtw.QLabel("Have you received an approval from the FD Logistics team?")
        )

        main_layout.addWidget(
            self.received_approval
        )

        main_layout.addWidget(qtw.QLabel("Approved by whom?"))
        main_layout.addWidget(self.approved_by)

        main_layout.addWidget(qtw.QLabel("When approved (date/time in Central Time)?"))
        main_layout.addWidget(self.approved_time)

        main_layout.addSpacing(15)
        main_layout.addWidget(
            qtw.QLabel("Take a photo or screenshot of the approved message and upload it")
        )

        main_layout.addWidget(self.approval_image)

        main_layout.addSpacing(15)
        
        ################

        main_layout.addWidget(qtw.QLabel("Please affirm the following:"))

        affirm_layout = qtw.QHBoxLayout()
        affirm_layout.addSpacing(10)

        indented_layout = qtw.QVBoxLayout()
        indented_layout.addWidget(self.confirm_attached_sheet)
        indented_layout.addWidget(self.confirm_insured)
        indented_widget = qtw.QWidget()
        indented_widget.setLayout(indented_layout)
        affirm_layout.addWidget(indented_widget)
        affirm_widget = qtw.QWidget()
        affirm_widget.setLayout(affirm_layout)
        main_layout.addWidget(affirm_widget)
        ################

        main_layout.addStretch()
        main_layout.addWidget(self.nav_bar)
        self.setLayout(main_layout)
        #}}}

    def refresh(self):
        #{{{
        super().refresh()

        if not self.received_approval.isChecked():
            self.nav_bar.continue_button.setEnabled(False)
            return
        if not self.confirm_attached_sheet.isChecked():
            self.nav_bar.continue_button.setEnabled(False)
            return
        if not self.confirm_insured.isChecked():
            self.nav_bar.continue_button.setEnabled(False)
            return

        if len(self.approved_by.text()) == 0:
            self.nav_bar.continue_button.setEnabled(False)
            return

        if len(self.page_state['approved_image']) == 0:
            self.nav_bar.continue_button.setEnabled(False)

        self.nav_bar.continue_button.setEnabled(True)
        #}}}

    def upload_files(self):
        #{{{
        import shutil, os
        from datetime import datetime
        from Sisyphus.Gui.Shipping import Model as mdl
        
        def rename(filename, prefix):
            username = self.application.whoami['username']
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
            file_ext = filename.split('.')[-1]
            new_filename = f"{prefix}-{username}-{timestamp}.{file_ext}"
            return new_filename

        def upload_file(filename, file_prefix, node_name):
            new_filename = rename(filename, file_prefix)
            new_full_filename = os.path.join(self.workflow.working_directory, new_filename)
            shutil.copy(filename, new_full_filename)

            image_id, checksum = mdl.upload_image(self.part_id, new_full_filename)
            self.page_state[node_name] = {
                "filename": new_filename,
                "image_id": image_id,
                "checksum": checksum
            }
            return True

        ok = upload_file(self.page_state['approved_image'], "LogisticsFinalApprovalEmail", "approval_info")
        logger.debug(f"(upload_files return) ok: {ok}")
        return ok
        #}}}
    
    def update_hwdb(self):
        return mdl.upload_shipping(self.workflow_state)

    def on_navigate_next(self):
        #{{{
        ok = super().on_navigate_next()
        logger.debug(f"(from super()) ok: {ok}")
        if not ok:
            return False

        ok = self.upload_files()
        logger.debug(f"(from upload_files) ok: {ok}")
        if not ok:
            return False

        ok = self.update_hwdb()
        logger.debug(f"(from update_hwdb) ok: {ok}")
        return ok
        #}}}
