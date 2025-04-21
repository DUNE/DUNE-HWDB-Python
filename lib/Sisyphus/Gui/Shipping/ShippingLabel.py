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
    _reportlab_available = True

except ModuleNotFoundError:
    _reportlab_available = False
import PIL.Image
import io
import base64
import tempfile

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
        
        if size is None:
            image_width, image_height = 3.0 * units.inch, 3.0 * units.inch
        else:
            image_width, image_height = size, size

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

    def draw_logo(self): #{{{
        cvs = self.cvs   
 
        logo_path = Sisyphus.get_path("resources/images/DUNE-logo.png")
        logo_pil = PIL.Image.open(logo_path)

        aspect_ratio = logo_pil.size[0]/logo_pil.size[1]
        image_width = self.page_usable_width
        image_height = image_width / aspect_ratio

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

        self.draw_qr(size=2.5*units.inch)
        self.blank_space(0.125 * units.inch)

        self.draw_label(self.workflow_state['part_info']['part_type_name'], 16, height=22.5)
        self.draw_label(self.workflow_state['part_info']['part_id'], 16, height=22.5)

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


