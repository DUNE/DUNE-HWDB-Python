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
        
import shutil, os
from datetime import datetime
        

###############################################################################

class Shipping4(PageWidget):
    page_name = "Shipping Workflow (4)"
    page_short_name = "Shipping (4)"

    def __init__(self, *args, **kwargs):
        #{{{
        super().__init__(*args, **kwargs)

        self.received_approval = zw.ZCheckBox("Yes, I have received an approval",
                    page=self, key='received_approval')
        self.approved_by = zw.ZLineEdit(page=self, key='approved_by')
        self.approved_time = zw.ZDateTimeEdit(page=self, key='approved_time')
        self.approval_image = zw.ZFileSelectWidget(page=self, key='approved_image')

        msg = "The DUNE Shipping Sheet has been securely attached to the shipment"
        self.confirm_attached_sheet = zw.ZCheckBox(page=self, text=msg, key="confirm_attached_sheet")

        msg = "The cargo has been adequately insured for transit"
        self.confirm_insured = zw.ZCheckBox(page=self, text=msg, key="confirm_insured")

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

        self.label1 = qtw.QLabel(
                "An email has been sent to the FD Logistics Team. "
                "Do not continue until you have received an approval from them."
        )
        self.label1.setWordWrap(True)
        main_layout.addWidget(self.label1)
        main_layout.addSpacing(15)

        self.label2 = qtw.QLabel("Have you received an approval from the FD Logistics team?")
        main_layout.addWidget(
            self.label2
        )

        main_layout.addWidget(
            self.received_approval
        )

        self.label3 = qtw.QLabel("Approved by whom?")
        main_layout.addWidget(self.label3)
        main_layout.addWidget(self.approved_by)

        self.label4 = qtw.QLabel("When approved (date/time in Central Time)?")
        main_layout.addWidget(self.label4)
        main_layout.addWidget(self.approved_time)

        main_layout.addSpacing(15)
        self.label5 =  qtw.QLabel("Take a photo or screenshot of the approved message and upload it")
        main_layout.addWidget(
           self.label5
        )

        main_layout.addWidget(self.approval_image)

        main_layout.addSpacing(15)
        
        ################

        self.label6 = qtw.QLabel("Please affirm the following:")
        main_layout.addWidget(self.label6)

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

        main_layout.addSpacing(20)

        # --- dynamically show/hide things ---
        select_pid_state = self.workflow_state.get("SelectPID", {})
        is_surf = select_pid_state.get("confirm_surf", False)
        if is_surf:
            self.upload_message = qtw.QLabel(f'''Click 'Continue' to upload the followings to the HWDB:\n\n'''\
                f'''  1. The selected photo of the approved message\n'''\
                f'''  2. Everything you have provided in this shipping checklist '''\
            )
        else:
            self.upload_message = qtw.QLabel(f'''Click 'Continue' to upload Everything you have provided in this shipping checklist to the HWDB:\n\n'''
            )

        
        self.upload_message.setWordWrap(True)
        self.upload_message.setStyleSheet("""
                font-size: 14pt;
            """)
        main_layout.addWidget(self.upload_message)

        ################

        main_layout.addStretch()
        main_layout.addWidget(self.nav_bar)
        self.setLayout(main_layout)
        #}}}

    def refresh(self):
        #{{{
        super().refresh()

        # --- dynamically show/hide things ---
        select_pid_state = self.workflow_state.get("SelectPID", {})
        is_surf = select_pid_state.get("confirm_surf", False)

        if not is_surf:
            self.label1.hide()
            self.label2.hide()
            self.received_approval.hide()
            self.label3.hide()
            self.approved_by.hide()
            self.label4.hide()
            self.approved_time.hide()
            self.label5.hide()
            self.approval_image.hide()
            self.label6.hide()
            self.confirm_attached_sheet.hide()
            self.confirm_insured.hide()
        else:
            self.label1.show()
            self.label2.show()
            self.received_approval.show()
            self.label3.show()
            self.approved_by.show()
            self.label4.show()
            self.approved_time.show()
            self.label5.show()
            self.approval_image.show()
            self.label6.show()
            self.confirm_attached_sheet.show()
            self.confirm_insured.show()
        
        if is_surf:
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
        else:
            self.nav_bar.continue_button.setEnabled(True)
        #}}}

    def upload_files(self):
        #{{{
        # --- dynamically show/hide things ---
        select_pid_state = self.workflow_state.get("SelectPID", {})
        is_surf = select_pid_state.get("confirm_surf", False)
        if is_surf:
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
                return True

            ok = upload_file(self.page_state['approved_image'], "LogisticsFinalApprovalEmail", "approval_info")
            return ok
        #}}}
    
    def update_hwdb(self):
        with self.wait():
            return dbt.upload_shipping(self.workflow_state)

    def on_navigate_next(self):
        #{{{
        ok = super().on_navigate_next()
        if not ok:
            return False

        # --- dynamically show/hide things ---
        select_pid_state = self.workflow_state.get("SelectPID", {})
        is_surf = select_pid_state.get("confirm_surf", False)
        if is_surf:
            ok = self.upload_files()
            if not ok:
                return False

        ok = self.update_hwdb()
        
        return ok
        #}}}
