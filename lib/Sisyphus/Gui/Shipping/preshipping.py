#!/usr/bin/env python

from Sisyphus.Configuration import config, USER_SETTINGS_DIR
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut

from Sisyphus.Utils.Terminal.Style import Style

from Sisyphus.Gui.Shipping.application import PageWidget
from Sisyphus.Gui.Shipping.application import ZLineEdit, ZTextEdit, ZCheckBox

from Sisyphus.Gui.Shipping.ShippingLabel import ShippingLabel

from PyQt5.QtCore import QSize, Qt, pyqtSignal, pyqtSlot
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

import base64

class PreShipping1(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create the interactive widgets on this page

        self.subcomp_caption = QLabel("Contents")

        self.table = QTableWidget(0, 3)
        self.table.verticalHeader().setVisible(False)

        self.confirm_list_checkbox = QCheckBox()
        self.confirm_list_checkbox.toggled.connect(self.toggle_confirm_list)
        self.confirm_hwdb_updated_checkbox = QCheckBox()
        self.confirm_hwdb_updated_checkbox.toggled.connect(self.toggle_hwdb_updated)
        
        # Create the actual layout and place the interactive widgets in it
        self._construct_page()

    def _construct_page(self):
        #{{{
        # This should create the visual appearance of the page. Any widgets
        # that are interactive should be created elsewhere, and then placed
        # inside the layout here. The reason for doing it this way is so
        # that the code creating and controlling dynamic elements won't be
        # cluttered by all the layout code here.

        screen_layout = QVBoxLayout()

        ########################################

        page_title = QLabel("Pre-Shipping Workflow (1)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        
        ########################################

        subcomp_list_layout = QVBoxLayout()
        subcomp_list_layout.addWidget( self.subcomp_caption )
        subcomp_list_layout.addSpacing(5)
        horizontal_header = self.table.horizontalHeader()
        horizontal_header.resizeSection(0, 200)
        horizontal_header.resizeSection(1, 275)
        horizontal_header.resizeSection(2, 275)
        self.table.setHorizontalHeaderLabels(['Sub-component PID',
                            'Component Type Name', 'Functional Position Name'])
        subcomp_list_layout.addWidget(self.table)
        subcomp_list_widget = QWidget()
        subcomp_list_widget.setLayout(subcomp_list_layout)
        screen_layout.addWidget(subcomp_list_widget)
        screen_layout.addSpacing(10)

        ########################################

        confirm_list_layout = QHBoxLayout()
        confirm_list_layout.addWidget( self.confirm_list_checkbox )
        confirm_list_layout.addWidget( QLabel("The list of components for this shipment is correct") )
        confirm_list_layout.addStretch()
        confirm_list_widget = QWidget()
        confirm_list_widget.setLayout(confirm_list_layout)
        screen_layout.addWidget(confirm_list_widget)
        screen_layout.addSpacing(10)

        ########################################

        confirm_hwdb_layout = QHBoxLayout()
        confirm_hwdb_layout.addWidget( self.confirm_hwdb_updated_checkbox )
        confirm_hwdb_layout.addWidget( QLabel("All necessary QA/QC information for these components "
                    "has been stored in the HWDB") )
        confirm_hwdb_layout.addStretch()
        confirm_hwdb_widget = QWidget()
        confirm_hwdb_widget.setLayout(confirm_hwdb_layout)
        screen_layout.addWidget(confirm_hwdb_widget)

        ########################################

        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
        #}}}

    def toggle_confirm_list(self, status):
        print("toggle confirm list")
        #self.tab_state['pre_shipping_1_confirm_list'] = status
        self.page_state['confirm_list'] = status
        self.save()

    def toggle_hwdb_updated(self, status):
        print("toggle hwdb updated")
        self.tab_state['pre_shipping_1_hwdb_updated'] = status
        self.page_state['hwdb_updated'] = status
        self.save()

    def restore(self):
        print("RESTORE: PreShipping1")
        setattr(self, "_loading", True)
        super().restore()

        #self.parent().update_title(f"{self.tab_state['part_id']} Pre-Shipping")
        self.populate_subcomps()


        #ch1 = self.tab_state.get('pre_shipping_1_confirm_list', False)
        #ch2 = self.tab_state.get('pre_shipping_1_hwdb_updated', False)
        ch1 = self.page_state.setdefault('confirm_list', False)
        ch2 = self.page_state.setdefault('hwdb_updated', False)

        self.confirm_list_checkbox.setChecked(ch1)
        self.confirm_hwdb_updated_checkbox.setChecked(ch2)
        #self.save()
        print("RESTORE: PreShipping1 (finished)")
        delattr(self, "_loading")

    def save(self):
        if getattr(self, "_loading", False):
            return
        print("SAVE: PreShipping1")
        self.workflow.save()


    def populate_subcomps(self):

        if self.tab_state.get('part_info', None) is None:
            subcomps = {}

        else:
            subcomps = self.tab_state['part_info'].setdefault('subcomponents', {})

        self.table.setRowCount(len(subcomps))
        for idx, subcomp in enumerate(subcomps.values()):
            print(subcomp)
            self.table.setItem(idx, 0, QTableWidgetItem(subcomp['Sub-component PID']))
            self.table.setItem(idx, 1, QTableWidgetItem(subcomp['Component Type Name']))
            self.table.setItem(idx, 2, QTableWidgetItem(subcomp['Functional Position Name']))
    #}}}


class PreShipping2(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.approver_name = ZLineEdit(parent=self, key='approver_name')
        self.approver_email = ZLineEdit(parent=self, key='approver_email')
        self.test_info = ZTextEdit(parent=self, key='test_info')

        self._construct_page()

    def _construct_page(self):
        #{{{
        screen_layout = QVBoxLayout()
        ########################################

        page_title = QLabel("Pre-Shipping Workflow (2)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        ################


        screen_layout.addWidget(
            QLabel("Provide the person's name and email address who has approved this shipment")
        )

        screen_layout.addWidget(
            QLabel("(For multiple email addresses, each address should be separated by a comma)")
        )

        ################

        contact_info_layout = QVBoxLayout(self)

        name_layout = QVBoxLayout()
        name_layout.addWidget(QLabel("Name"))
        #name_layout.addWidget(QLineEdit("Joe Schmoe"))
        name_layout.addWidget(self.approver_name)
        name_layout_widget = QWidget(self)
        name_layout_widget.setLayout(name_layout)

        email_layout = QVBoxLayout()
        email_layout.addWidget(QLabel("Email"))
        email_layout.addWidget(self.approver_email)
        email_layout_widget = QWidget(self)
        email_layout_widget.setLayout(email_layout)

        contact_info_layout.addWidget(name_layout_widget)
        contact_info_layout.addWidget(email_layout_widget)


        contact_info_layout_widget = QWidget(self)
        contact_info_layout_widget.setLayout(contact_info_layout)

        screen_layout.addWidget(contact_info_layout_widget)

        ################

        test_info_label = QLabel("Provide information on where the corresponding QA/QC test results "
                "can be found (e.g., link(s) to test results in the HWDB) and a EDMS or "
                "doc-DB # of the corresponding documentation.")
        test_info_label.setWordWrap(True)
        screen_layout.addWidget(test_info_label)

        test_info_layout = QVBoxLayout()
        #test_info_layout.addWidget(QTextEdit(self))
        test_info_layout.addWidget(self.test_info)
        test_info_widget = QWidget()
        test_info_widget.setLayout(test_info_layout)

        screen_layout.addWidget(test_info_widget)




        ################
        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
        #}}}
    #}}}

class PreShipping3a(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.radio_domestic = QRadioButton("Domestic")
        self.radio_international = QRadioButton("International")

        self.radio_domestic.toggled.connect(self.select_shipping_service_type)
        self.radio_international.toggled.connect(self.select_shipping_service_type)

        self.hts_code = ZLineEdit(parent=self, key='hts_code')
        
        self.shipment_origin = ZLineEdit(parent=self, key='shipment_origin')
        self.dimension = ZLineEdit(parent=self, key='dimension')
        self.weight = ZLineEdit(parent=self, key='weight')

        self._construct_page()

    def select_shipping_service_type(self):
        rb = self.sender()
        if not rb.isChecked():
            return

        if rb is self.radio_domestic:
            self.page_state['shipping_service_type'] = 'Domestic'
        elif rb is self.radio_international:
            self.page_state['shipping_service_type'] = 'International'

        self.save()
    
    def restore(self):
        shipping_service_type = self.page_state.setdefault('shipping_service_type', 'Domestic')

        if shipping_service_type == 'International':
            self.radio_international.setChecked(True)
        else:
            self.radio_domestic.setChecked(True)
        


    def _construct_page(self):
        #{{{
        screen_layout = QVBoxLayout()
        ########################################

        page_title = QLabel("Pre-Shipping Workflow (3)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        ################


        group_box_1 = QGroupBox()

        group_box_1_layout = QVBoxLayout()
        group_box_1_layout.addWidget(
            QLabel("Will this be a domestic or international shipment?")
        )



        group_box_1_layout.addWidget(self.radio_domestic)
        group_box_1_layout.addWidget(self.radio_international)
       
        group_box_2 = QGroupBox()
        group_box_2_layout = QVBoxLayout() 
        intl_label_1 = QLabel("For international shipment:")
        intl_label_2 = QLabel(
                "Provide your Harmonized Tariff Schedule (HTS) code.\n"
                " - Use the HTS code that your institution or lab used in the past successfully\n"
                " - Else, for Equipment and Materials for the LBNF & DUNE Scientific Projects, "
                    "use 8543.90.8845 (parts of particle accelerators"
        )
        intl_label_2.setWordWrap(True)
        intl_label_2.setStyleSheet("""
                font-size: 10pt;
            """)
        group_box_2_layout.addWidget(intl_label_1)
        group_box_2_layout.addWidget(intl_label_2)
        group_box_2_layout.addWidget(self.hts_code)
        group_box_2.setLayout(group_box_2_layout)
    
        group_box_1_layout.addWidget(group_box_2)
    
        group_box_1.setLayout(group_box_1_layout)

        screen_layout.addWidget(group_box_1)

        ################
        ################

        screen_layout.addWidget(QLabel("Provide the shipment's origin:"))
        screen_layout.addWidget(self.shipment_origin)

        ################


        dim_wt_label = QLabel(
                "Provide the dimension (length x width x height) and weight of your shipment. "
                "Don't forget to provide their units as well (inches, m, lbs, kg, etc.)"
        )
        dim_wt_label.setWordWrap(True)
        screen_layout.addWidget(dim_wt_label)

        dim_wt_layout = QVBoxLayout()

        dim_layout = QHBoxLayout()
        dim_layout.addWidget(QLabel("Dimension"))
        dim_layout.addWidget(self.dimension)
        dim_widget = QWidget()
        dim_widget.setLayout(dim_layout)

        wt_layout = QHBoxLayout()
        wt_layout.addWidget(QLabel("Weight"))
        wt_layout.addWidget(self.weight)
        wt_widget = QWidget()
        wt_widget.setLayout(wt_layout)

        dim_wt_layout.addWidget(dim_widget)
        dim_wt_layout.addWidget(wt_widget)
        dim_wt_widget = QWidget()
        dim_wt_widget.setLayout(dim_wt_layout)
        screen_layout.addWidget(dim_wt_widget)

        ################
        ################

        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
        #}}}
    #}}}

class PreShipping3b(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.freight_forwarder = ZLineEdit(parent=self, key='freight_forwarder')
        self.mode_of_transportation = ZLineEdit(parent=self, key='mode_of_transportation')
        self.expected_arrival_time = ZLineEdit(parent=self, key='expected_arrival_time')

        self._construct_page()

    def _construct_page(self):
        #{{{
        screen_layout = QVBoxLayout()
        ########################################

        page_title = QLabel("Pre-Shipping Workflow (3b)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        ################
        ################

        ff_label = QLabel(
                "Provide name(s) of your Freight Forwarder (FF; such as FedEx or UPS. "
                "USPS is not allowed) and mode(s) of transportation (truck, air, ship, "
                "rail, etc.):"
        )
        ff_label.setWordWrap(True)
        screen_layout.addWidget(ff_label)

        ff_mode_layout = QVBoxLayout()

        ff_layout = QHBoxLayout()
        ff_layout.addWidget( QLabel("Name of FF:") )
        ff_layout.addWidget( self.freight_forwarder )
        ff_widget = QWidget()
        ff_widget.setLayout(ff_layout)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget( QLabel("Mode:") )
        mode_layout.addWidget( self.mode_of_transportation )
        mode_widget = QWidget()
        mode_widget.setLayout(mode_layout)

        ff_mode_layout.addWidget(ff_widget)
        ff_mode_layout.addWidget(mode_widget)
        ff_mode_widget = QWidget()
        ff_mode_widget.setLayout(ff_mode_layout)

        screen_layout.addWidget(ff_mode_widget)

        ################

        screen_layout.addSpacing(10)



        screen_layout.addWidget(QLabel("Provide the expected arrival time:"))
        screen_layout.addWidget( self.expected_arrival_time)


        ################

        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
        #}}}
    #}}}

class PreShipping4(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.confirm_email_contents = ZCheckBox('Yes, this looks correct',
                        parent=self, key='confirm_email_contents')

        self._construct_page()

    def _construct_page(self):
        #{{{

        screen_layout = QVBoxLayout()
        ########################################

        page_title = QLabel("Pre-Shipping Workflow (4)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        ################

        screen_layout.addWidget(
            QLabel("(add some controls here for previewing email message & csv file)")
        )

        ################

        screen_layout.addSpacing(15)

        screen_layout.addWidget(
            QLabel("Does this information look correct?")
        )
        screen_layout.addWidget(
            #QCheckBox("Yes, this looks correct")
            self.confirm_email_contents
        )

        ################

        screen_layout.addSpacing(15)

        screen_layout.addWidget(
            QLabel("Clicking 'continue' will send this email to the FD Logistics Team")
        )

        ################
        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
        #}}}

    def on_navigate_next(self):
        sender = 'alexcwagner@gmail.com'
        receivers = 'alexcwagner@gmail.com'
        message = 'This is a test email message.'

        try:
            smtp_obj = smtplib.SMTP('localhost')
            smtp_obj.sendmail(sender, receivers, message)
            print("Successfully sent email")
        except smtplib.SMTPException:
            Style.error.print("SMTPException: unable to send email")
        except Exception as exc:
            Style.error.print(f"Error sending email: {exc}")

    def restore(self):
        super().restore()
        self.generate_email()
        self.generate_csv()

    def generate_email(self):
        ...

    def generate_csv(self):
        #{{{
        print("Creating CSV...")
        
        self.csv_filename = f"{self.tab_state['part_id']}-preshipping.csv"

        with open(self.csv_filename, 'w') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')

            csvwriter.writerow([
                "Dimension",
                self.tab_state['PreShipping3a']['dimension']
            ])
            csvwriter.writerow([
                "Weight",
                self.tab_state['PreShipping3a']['weight']
            ])
            csvwriter.writerow([
                "Freight Forwarder name",
                self.tab_state['PreShipping3b']['freight_forwarder']
            ])
            csvwriter.writerow([
                "Mode of Transportation",
                self.tab_state['PreShipping3b']['mode_of_transportation']
            ])
            csvwriter.writerow([
                "Expected Arrival Date (CST)",
                self.tab_state['PreShipping3b']['expected_arrival_time']
            ])
            csvwriter.writerow([
                "Shipment's origin",
                self.tab_state['PreShipping3a']['shipment_origin']
            ])
            csvwriter.writerow([
                "HTS code",
                self.tab_state['PreShipping3a']['hts_code']
            ])
            csvwriter.writerow([])
            csvwriter.writerow([
                "QA/QC related information for this shipment can be found here",
                self.tab_state['PreShipping2']['test_info']
            ])
            csvwriter.writerow([])
            csvwriter.writerow([
                "System Name (ID)",
                "TBD"
            ])
            csvwriter.writerow([
                "Subsystem Name (ID)",
                "TBD"
            ])
            csvwriter.writerow([
                "Component Type Name (ID)",
                "TBD"
            ])
            csvwriter.writerow([
                "DUNE PID",
                self.tab_state['part_id']
            ])
            csvwriter.writerow([])
            csvwriter.writerow([
                "Sub-component PID",
                "Component Type Name",
                "Func. Pos. Name"
            ])
        #}}}
    #}}}
        


class PreShipping5(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.received_acknowledgement = ZCheckBox("Yes, I have received an acknowledgement",
                    parent=self, key='received_acknowledgement')

        self.acknowledged_by = ZLineEdit(parent=self, key='acknowledged_by')

        self.radio_no_damage = QRadioButton("No obvious damage to report")
        self.radio_damage = QRadioButton("There is some damage")
        self.radio_no_damage.toggled.connect(self.select_damage_status)
        self.radio_damage.toggled.connect(self.select_damage_status)

        self.damage_description = ZTextEdit(parent=self, key='damage_description')


        self._construct_page()

    def select_damage_status(self):
        rb = self.sender()
        if not rb.isChecked():
            return

        if rb is self.radio_no_damage:
            self.page_state['damage_status'] = 'no damage'
        elif rb is self.radio_damage:
            self.page_state['damage'] = 'damage'

        self.save()

    def restore(self):
        damage_status = self.page_state.setdefault('damage_status', 'no damage')

        if damage_status == 'damage':
            self.radio_damage.setChecked(True)
        else:
            self.radio_no_damage.setChecked(True)

    def _construct_page(self):
        screen_layout = QVBoxLayout()
        ########################################

        page_title = QLabel("Pre-Shipping Workflow (5)")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)

        ################

        label1 = QLabel(
                "An email has been sent to the FD Logistics Team."
                "Do not continue until you have received an acknowledgement from them."
        )
        label1.setWordWrap(True)
        screen_layout.addWidget(label1)
        screen_layout.addSpacing(15)


        screen_layout.addWidget(
            QLabel("Have you received an acknowledgement from the FD Logistics team?")
        )

        screen_layout.addWidget(
            self.received_acknowledgement
        )

        screen_layout.addWidget(QLabel("Acknowledged by whom?"))
        screen_layout.addWidget(self.acknowledged_by)


        screen_layout.addSpacing(15)
        screen_layout.addWidget(
            QLabel("Is there any visually obvious damage on the shipment?")
        )

        screen_layout.addWidget(self.radio_no_damage)
        screen_layout.addWidget(self.radio_damage)

        screen_layout.addSpacing(5)
        screen_layout.addWidget(QLabel("If there is damage, describe the damage"))
        screen_layout.addWidget(self.damage_description)





        ################

        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
    #}}}

class PreShipping6(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.pdf_view = QLabel()

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
        screen_layout.addWidget(self.pdf_view)


        ################
        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)

        #self.generate_shipping_sheet()

    def restore(self):
        self.generate_shipping_sheet()

    def generate_shipping_sheet(self):

        filename = f"{self.tab_state['part_id']}-shipping-label.pdf"

        ShippingLabel(filename, self.tab_state, show_logo=False, debug=False)

        return


    def update_hwdb(self):
        ts = self.tab_state
        checklist = {
            "DATA": {
                "Pre-Shipping Checklist": [
                    {"POC name": ts['SelectPID']['user_name']},
                    {"POC Email": [s.strip() for s in ts['SelectPID']['user_email'].split(',')]},
                    {"System Name (ID)": f"{ts['part_info']['system_name']}"
                                        f" ({ts['part_info']['system_id']})"},
                    {"Subsystem Name (ID)":  f"{ts['part_info']['subsystem_name']}"
                                        f" ({ts['part_info']['subsystem_id']})"},
                    {"Component Type Name (ID)": f"{ts['part_info']['part_type_name']}"
                                        f" ({ts['part_info']['part_type_id']})"},
                    {"DUNE PID": ts['part_info']['part_id']},
                    {"QA/QC related info Line 1": ts['PreShipping2']['test_info']},
                    {"HTS code": ts['PreShipping3a']['hts_code'] 
                                       if ts['PreShipping3a']['shipping_service_type'] 
                                            != 'Domestic' else None },
                    {"Origin of this shipment": ts['PreShipping3a']['shipment_origin']},
                    {"Dimension of this shipment": ts['PreShipping3a']['dimension']},
                    {"Weight of this shipment": ts['PreShipping3a']['weight']},
                    {"Freight Forwarder name": ts['PreShipping3b']['freight_forwarder']},
                    {"Mode of Transportation": ts['PreShipping3b']['mode_of_transportation']},
                    {"Expected Arrival Date (CT)": ts['PreShipping3b']['expected_arrival_time']},
                    {"FD Logistics team acknoledgement (name)": ts['PreShipping5']['acknowledged_by']},
                    {"FD Logistics team acknoledgement (date in CT)": ""},
                    {"Visual Inspection (YES = no damage)": ""},
                    {"Image ID for this Shipping Sheet": ""}
                ],
                "SubPIDs": [
                    {"(Test Type 002 (My Sub Comp 2)": "D00599800002-00057)"},
                    {"(Test Type 003 (My Sub Comp 1)": "D00599800003-00001)"}
                ]
            }
        }
        logger.info(json.dumps(checklist, indent=4))


    def on_navigate_next(self):
        super().on_navigate_next()

        self.update_hwdb()        

    #}}}

class PreShippingComplete(PageWidget):
    #{{{
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        screen_layout = QVBoxLayout()
        ########################################

        page_title = QLabel("Pre-Shipping Workflow Complete")
        page_title.setStyleSheet("""
                font-size: 14pt;
                font-weight: bold;
            """)
        page_title.setAlignment(Qt.AlignCenter)
        screen_layout.addWidget(page_title)
        ################
        screen_layout.addStretch()

        self.nav_bar = self.parent().NavBar(self.parent())
        screen_layout.addWidget(self.nav_bar)

        self.setLayout(screen_layout)
    #}}}
