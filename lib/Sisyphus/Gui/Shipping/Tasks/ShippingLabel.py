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

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib import units
    from reportlab.lib.utils import ImageReader
    _reportlab_available = True

except ModuleNotFoundError:
    _reportlab_available = False
import PIL.Image
import io
import base64
import tempfile

# needed to generate bar-code
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import code128
from reportlab.graphics.barcode import createBarcodeDrawing


###############################################################################

def color(i):
    r = (i & 0xff0000) / 0xff0000
    g = (i & 0x00ff00) / 0x00ff00
    b = (i & 0x0000ff) / 0x0000ff
    return (r, g, b)

class ShippingLabel:
    def __init__(self, filename, workflow_state, show_logo=False, debug=False):
        self.filename = filename
        self.workflow_state = workflow_state
        self.show_logo = show_logo
        self.debug = debug

        if not _reportlab_available:
            print("Label generation unavailable. To enable label generation, install reportlab.\n"
                "Try: 'pip install reportlab'")
            return

        self.create()

    def draw_rectangle(self, left, top, width, height, stroke=None, fill=None): #{{{
        cvs = self.cvs

        cvs.saveState()

        if stroke is not None:
            cvs.setStrokeColorRGB(*color(stroke), 0.25)

        if fill is not None:
            do_fill = 1
            cvs.setFillColorRGB(*color(fill), 0.25)
        else:
            do_fill = 0

        cvs.rect(left, top-height, width, height, stroke=1, fill=do_fill)
        cvs.restoreState()
        #}}}

    def mark_geometry(self): #{{{
        cvs = self.cvs

        cvs.saveState()
        for y in range(0, 1+int(self.page_height), 9):
            if y % 72 == 0:
                cvs.setStrokeColorRGB(*color(0x99ccff))
            else:
                cvs.setStrokeColorRGB(*color(0xddeeff))

            p = cvs.beginPath()
            p.moveTo(0, y)
            p.lineTo(self.page_width, y)
            p.close()
            cvs.drawPath(p, stroke=1, fill=0)
        cvs.restoreState()

        cvs.saveState()
        cvs.rotate(-90)
        for y in range(0, 1+int(self.page_width), 9):
            if y % 72 == 0:
                cvs.setStrokeColorRGB(*color(0x99ccff))
            else:
                cvs.setStrokeColorRGB(*color(0xddeeff))

            p = cvs.beginPath()
            p.moveTo(0, y)
            p.lineTo(-self.page_height, y)
            p.close()
            cvs.drawPath(p, stroke=1, fill=0)
        cvs.restoreState()
        
        cvs.saveState()
        for y in range(0, 1+int(self.page_height), 9):
            if y % 72 == 0:
                font_size = 8
                cvs.setFillColorRGB(*color(0xff8888))
            else:
                font_size = 6
                cvs.setFillColorRGB(*color(0xffaaaa))
            cvs.setFont("Helvetica-Bold", font_size)
            cvs.drawCentredString(18, y-font_size/3, str(y))
        cvs.restoreState()

        cvs.saveState()
        cvs.rotate(-90)
        for y in range(0, 1+int(self.page_width), 9):
            if y == 18:
                continue
            if y % 72 == 0:
                font_size = 8
                cvs.setFillColorRGB(*color(0xff8888))
            else:
                font_size = 6
                cvs.setFillColorRGB(*color(0xffaaaa))
            cvs.setFont("Helvetica-Bold", font_size)
            cvs.drawCentredString(-18, y-font_size/3, str(y))
        cvs.restoreState() 
        #}}}

    def draw_qr(self, size=None): #{{{
        cvs = self.cvs
 
        img_bytes = base64.b85decode(self.workflow_state['part_info']['qr_code'].encode())
        img_obj = PIL.Image.open(io.BytesIO(img_bytes))
        #cropped_obj = img_obj.crop((40, 40, 410, 410))
       
        size = size or 3.0 * units.inch
 
        image_width, image_height = size, size

        if self.current_top - image_height < 0.5 * units.inch:
            # There is less than half an inch remaining on the page, so we
            # should start a new page.
            cvs.showPage()
            self.current_top = self.page_height - self.top_margin


        if self.debug:
            self.draw_rectangle(
                self.left_margin,
                self.current_top,
                self.page_usable_width,
                image_height,
                stroke=0x00ff00,
                fill=0xccffcc) 

        with tempfile.NamedTemporaryFile() as tf:
            #cropped_obj.save(tf, 'png')
            img_obj.save(tf, 'png')
            cvs.drawImage(
                tf.name,
                (self.page_width - image_width) * 0.5,
                self.current_top - image_height,
                image_width,
                image_height,
                mask=[255,256,255,256,255,256])
        self.current_top -= image_height
        #}}}

    #---------------------
    def draw_codes_side_by_side(self):
        """
        Draw QR (left) and barcode (right) with labels under each; 
        matches Swift UI style.
        """
        cvs = self.cvs

        pid = self.workflow_state['part_info']['part_id']
        test_type = self.workflow_state['part_info']['part_type_name']

        dbver = ""
        if config.config_data["active profile"] == "development":
            dbver = "dev"
        else:
            dbver = "pro"

        # Layout parameters
        #qr_size = 2.5 * units.inch
        #barcode_height = 0.75 * units.inch
        #barcode_width = 3.75 * units.inch
        #gap = 0.75 * units.inch

        # ----- Layout tuning to match iPad -----
        qr_size = 2.40 * units.inch       # slightly smaller QR
        barcode_height = 0.55 * units.inch
        barcode_width  = 3.20 * units.inch
        horizontal_gap = 0.70 * units.inch
        shift_x          = 0.70 * units.inch             # shift both QR + barcode rightward
        barcode_offset_y = 0.45 * units.inch             # lower the barcode slightly

        y_top = self.current_top

        x_left  = self.left_margin + shift_x
        x_right = x_left + qr_size + horizontal_gap


        # ----- Load QR -----
        qr_bytes = base64.b85decode(self.workflow_state['part_info']['qr_code'])
        qr_img = PIL.Image.open(io.BytesIO(qr_bytes))
        #qr_img = qr_img.resize((int(qr_size), int(qr_size)))
        qr_img = qr_img.resize((int(qr_size), int(qr_size)), PIL.Image.NEAREST)
        qr_reader = ImageReader(qr_img)

        cvs.drawImage(qr_reader, x_left, y_top - qr_size, qr_size, qr_size)

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # ----- Load Barcode from bar_code -----
        #bar_bytes = base64.b85decode(self.workflow_state['part_info']['bar_code'])
        #bar_img = PIL.Image.open(io.BytesIO(bar_bytes))

        # Upscale barcode sharply (fixes low-res blur)
        #bw, bh = bar_img.size
        #scale_factor = 5
        #bar_img = bar_img.resize((bw * scale_factor, bh * scale_factor), PIL.Image.NEAREST)

        
        # Resize / scale barcode to desired size
        #bar_img = bar_img.resize((int(barcode_width), int(barcode_height)))
        #bar_img = bar_img.resize((int(barcode_width), int(barcode_height)), PIL.Image.NEAREST)

        #bar_reader = ImageReader(bar_img)

        #cvs.drawImage(bar_reader, x_right, y_top - barcode_height,
        #                  barcode_width, barcode_height)

        # ----- Generate crisp Code128 barcode -----
        barcode_value = pid
        barcode_obj = code128.Code128(
            barcode_value,
            barHeight=barcode_height,
            barWidth=1.15,    # good thickness for print clarity
        )

        # Draw directly on PDF canvas
        barcode_y = y_top - barcode_height - barcode_offset_y
        barcode_obj.drawOn(
            cvs,
            x_right,
            barcode_y
        )
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        
        # ----- Labels under each -----
        #def label(text, x_center, y):
        #    cvs.setFont("Helvetica-Bold", 12)
        #    cvs.drawCentredString(x_center, y, text)

        # centers
        #qr_center = x_left + qr_size / 2
        #bar_center = x_right + barcode_width / 2

        # Label Y positioning (just below QR)
        #y = y_top - qr_size - 14
        #y_bar = y_top - 3*barcode_height

        #---
        #label(dbver, qr_center, y)
        #label(dbver, bar_center, y_bar)
        #y -= 14
        #y_bar -= 14

        #label(test_type, qr_center, y)
        #label(test_type, bar_center, y_bar)
        #y -= 14
        #y_bar -= 14

        #label(pid, qr_center, y)
        #label(pid, bar_center, y_bar)
        #---
        

        # Move down page cursor
        #self.current_top = y - 0.35 * units.inch
        #self.current_top = y_bar - 0.35 * units.inch

        # ONE Combined Label Block (centered)
        def label(text, x_center, y):
            cvs.setFont("Helvetica-Bold", 14)
            cvs.drawCentredString(x_center, y, text)

        # centers
        qr_center = x_left + qr_size / 2
        bar_center = x_right + barcode_width / 2

        # Center between the two
        combined_center = (qr_center + bar_center) / 2

        # Choose the lower of QR bottom or barcode bottom
        label_y_start = min(
            y_top - qr_size,
            barcode_y
        ) - 30  # slight spacing

        # Render centered labels
        y_lbl = label_y_start
        label(dbver,     combined_center, y_lbl);  y_lbl -= 14
        label(test_type, combined_center, y_lbl);  y_lbl -= 14
        label(pid,       combined_center, y_lbl);  y_lbl -= 16

        # Update vertical cursor
        self.current_top = y_lbl - 0.35 * units.inch
        
    #---------------------
        
    def draw_logo(self): #{{{
        cvs = self.cvs   
 
        logo_path = Sisyphus.get_path("resources/images/DUNE-logo.png")
        logo_pil = PIL.Image.open(logo_path)

        aspect_ratio = logo_pil.size[0]/logo_pil.size[1]
        image_width = self.page_usable_width
        image_height = image_width / aspect_ratio
        
        if self.current_top - image_height < 0.5 * units.inch:
            # There is less than half an inch remaining on the page, so we
            # should start a new page.
            cvs.showPage()
            self.current_top = self.page_height - self.top_margin

        if self.debug:
            self.draw_rectangle(
                self.left_margin,
                self.current_top,
                self.page_usable_width,
                image_height,
                stroke=0x00ffff,
                fill=0xccffff)

        cvs.drawImage(
            logo_path,
            self.left_margin,
            self.current_top - image_height,
            image_width,
            image_height,
            mask=[0, 0, 0, 0, 0, 0])

        self.current_top -= image_height
        #}}}

    def blank_space(self, space): #{{{
        cvs = self.cvs

        # Don't worry about going to a new page here. Let the next non-blank
        # item figure it out. Otherwise, we would end up going to a new page
        # only to put the blank space right at the top.

        if self.debug:
            self.draw_rectangle(
                    self.left_margin,
                    self.current_top,
                    self.page_usable_width,
                    space,
                    stroke=0x888888,
                    fill=0xcccccc)

        self.current_top -= space                    
        #}}}

    def draw_label(self, text, font_size=12, box=False, width=None, height=None): #{{{
        
        cvs = self.cvs

        if height is None:
            height = font_size * 4/3
        v_off = (height - font_size * 4/3) / 2
        
        if self.current_top - height < 0.5 * units.inch:
            # There is less than half an inch remaining on the page, so we
            # should start a new page.
            cvs.showPage()
            self.current_top = self.page_height - self.top_margin

        cvs.saveState()

        cvs.setFont("Helvetica-Bold", font_size)

        if self.debug:
            self.draw_rectangle(
                    self.left_margin,
                    self.current_top,
                    self.page_usable_width,
                    height,
                    stroke=0xff0000,
                    fill=0xffcccc)

        if type(text) is str:
            text = [text]
        if width is None:
            width = [self.page_usable_width/len(text)] * len(text)

        if len(width) > 1:
            gap = (self.page_usable_width - sum(width)) / (len(width) - 1)
        else:
            gap = 0

        left_edge = [ sum(width[0:c]) + gap*c for c, w in enumerate(width) ]

        #print(f"left_edge: {left_edge}, width: {width}, gap: {gap}")

        for coltext, colleft, colwidth in zip(text, left_edge, width):
            my_left_edge = self.left_margin + colleft
            my_center = my_left_edge + colwidth/2

            if box:
                self.draw_rectangle(
                        my_left_edge,
                        self.current_top,
                        colwidth,
                        height,
                        stroke=None,
                        fill=0xffffff)

            cvs.drawCentredString(
                my_center,
                self.current_top - font_size - v_off,
                coltext)

        cvs.restoreState()

        self.current_top -= height
        #}}}

    def create(self):
        #{{{
        self.page_width, self.page_height = 8.5 * units.inch, 11.0 * units.inch
        self.left_margin, self.right_margin, self.top_margin, self.bottom_margin = [
                x * units.inch for x in (0.5, 0.5, 0.5, 0.5) ]
        self.page_usable_width = self.page_width - self.left_margin - self.right_margin
        self.current_top = self.page_height - self.top_margin


        cvs = self.cvs = canvas.Canvas(self.filename)
        cvs.setTitle(f"Shipping Label: {self.workflow_state['part_info']['part_id']}")
        cvs.setAuthor(f"HWDB Python Utility {Sisyphus.version}")

        cvs.setPageSize([ self.page_width, self.page_height ])

        if self.debug:
            self.mark_geometry()

        if self.show_logo:
            self.draw_logo()

        self.draw_label("DUNE Shipping Sheet", 24, height=0.5*units.inch)
        self.blank_space(0.375 * units.inch)

        #--------------------------------------------
        #self.draw_qr(size=2.5*units.inch)
        #self.blank_space(0.125 * units.inch)

        #self.draw_label(self.workflow_state['part_info']['part_type_name'], 16, height=22.5)
        #self.draw_label(self.workflow_state['part_info']['part_id'], 16, height=22.5)
        self.draw_codes_side_by_side()
        self.blank_space(0.25 * units.inch)
        #--------------------------------------------
        
        self.blank_space(0.25 * units.inch)


        self.draw_label("Responsible Person's Name", 14)
        self.draw_label(
                self.workflow_state['PreShipping3']['approver_name'], 
                font_size=14,
                box=True)
        
        self.blank_space(0.125 * units.inch)
        
        self.draw_label("Email Address(es)", 14)
        self.draw_label(
                self.workflow_state['PreShipping3']['approver_email'], 
                font_size=14,
                box=True)

        self.blank_space(0.125 * units.inch)
       
        gap = 1/8 * units.inch
        column_widths = [ (self.page_usable_width - gap) / 2 ] * 2 
        self.draw_label(
                ['System Name', 'Subsystem Name'], 
                font_size=14, 
                box=False, 
                width=column_widths)

        text = [ 
            f"{self.workflow_state['part_info']['system_name']} "
                        f"({self.workflow_state['part_info']['system_id']})",
            f"{self.workflow_state['part_info']['subsystem_name']} "
                        f"({self.workflow_state['part_info']['subsystem_id']})"]
        self.draw_label(
                text,
                font_size=14, 
                box=True, 
                width=column_widths)

        self.blank_space(0.25 * units.inch)

        gap = 0
        column_widths = [ (self.page_usable_width - 2 * gap) / 3 ] * 3
        self.draw_label(
                ['Sub-component PID', 'Component Type Name', 'Func. Pos. Name'], 
                font_size=12, 
                box=True, 
                width=column_widths)
        for subcomp in self.workflow_state['part_info']['subcomponents'].values():
            text = [
                subcomp['Sub-component PID'], 
                subcomp['Component Type Name'], 
                subcomp['Functional Position Name']
            ]
            self.draw_label(
                    text, 
                    font_size=10, 
                    box=True, 
                    width=column_widths)


        cvs.showPage()
        cvs.save()

        #}}}


