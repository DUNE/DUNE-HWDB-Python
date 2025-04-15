#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/HWDBUtility/PDFLabels.py
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""
from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut
import multiprocessing.dummy as mp # multiprocessing interface, but uses threads instead
import io
import PIL.Image
from copy import deepcopy
import tempfile
import json
from collections import namedtuple

coord = namedtuple("coord", ['x', 'y'])
size = namedtuple("size", ['w', 'h'])
bbox1 = namedtuple("bbox1", ['x', 'y', 'w', 'h'])
bbox2 = namedtuple("bbox2", ['x1', 'y1', 'x2', 'y2'])
addtuple = lambda a, b: type(a)(*(sum(x) for x in zip(a, b)))
scaletuple = lambda a, b: type(b)(*(a * x for x in b))

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib import units
    _reportlab_available = True

except ModuleNotFoundError:
    _reportlab_available = False

_debug = False

_image_dimensions = {
    "qr": size(450, 450),
    "bar": size(688, 280),
}

_crop_dimensions = {
    "qr": size(370, 370),
    "bar": size(628, 178),
}

_crop_offset = {
    "qr": coord(40, 40),
    "bar": coord(30, 11),
}


_crop_bbox2 = {
    "qr": bbox2(*_crop_offset['qr'], *addtuple(_crop_offset['qr'], _crop_dimensions["qr"])),
    "bar": bbox2(*_crop_offset['bar'], *addtuple(_crop_offset['bar'], _crop_dimensions["bar"])),
}

label_templates = {  #{{{
    "A4": 
    {
        "11x4":
        {
            "name": "A4-11x4",
            "description": '''A4 (210×297 mm), 51.5×26.6 mm labels, 44 per sheet''',
            "units": "mm",
            "pagesize": (210, 297),
            "labelsize": (51.5, 26.6),
            "vertical_offsets": [2.2 + 26.6 * n for n in range(11)],
            "horizontal_offsets": [2.0 + 51.5 * n for n in range(4)],
            "margin": 1.33,
        },
        "4x3":
        {
            "name": "A4-4x3",
            "description": '''A4 (210×297 mm), 67×72 mm labels, 12 per sheet''',
            "units": "mm",
            "pagesize": (210, 297),
            "labelsize": (67, 72),
            "vertical_offsets": [2.5 + 73 * n for n in range(4)],
            "horizontal_offsets": [3.0 + 69 * n for n in range(3)],
            "margin": 3.35,
        }
    },
    "letter":
    {
        "2x2":
        {
            "name": "Letter-2x2",
            "description": '''Letter (8.5”×11”), 5”×3.5” labels, 4 per sheet''',
            "units": "inch",
            "pagesize": (8.5, 11.0),
            "labelsize": (3.5, 5.0),
            "vertical_offsets": [0.5, 5.5],
            "horizontal_offsets": [0.5, 4.5],
            "margin": 0.175,
        },
        "3x2":
        {
            "name": "Letter-3x2",
            "description": '''Letter (8.5”×11”), 4”×3.333” labels, 6 per sheet''',
            "units": "inch",
            "pagesize": (8.5, 11.0),
            "labelsize": (4.0, 3.33333),
            "vertical_offsets": [0.5, 3.83333, 7.16667],
            "horizontal_offsets": [0.15625, 4.34375],
            "margin": 0.16667,
        },
        "test":
        {
            "name": "Letter-3x2-test",
            "description": '''TEST Letter (8.5”×11”), 4”×3.333” labels, 6 per sheet''',
            "units": "inch",
            "pagesize": (8.5, 11.0),
            "labelsize": (3.75, 3.33333),
            "vertical_offsets": [0.5, 3.83333, 7.16667],
            "horizontal_offsets": [0.15625, 4.34375],
            "margin": 0.16667,
        },
        "4x2":
        {
            "name": "Letter-4x2",
            "description": '''Letter (8.5”×11”), 4”×2.5” labels, 8 per sheet''',
            "units": "inch",
            "pagesize": (8.5, 11.0),
            "labelsize": (4.0, 2.5),
            "vertical_offsets": [0.5, 3.0, 5.5, 8.0],
            "horizontal_offsets": [0.15625, 4.34375],
            "margin": 0.125,
        },
        "5x2":
        {
            "name": "Letter-5x2",
            "description": '''Letter (8.5”×11”), 4”×2” labels, 10 per sheet''',
            "units": "inch",
            "pagesize": (8.5, 11.0),
            "labelsize": (4.0, 2.0),
            "vertical_offsets": [0.5, 2.5, 4.5, 6.5, 8.5],
            "horizontal_offsets": [0.15625, 4.34375],
            "margin": 0.1,
        },
        "6x2":
        {
            "name": "Letter-6x2",
            "description": '''Letter (8.5”×11”), 4”×1.5” labels, 12 per sheet''',
            "units": "inch",
            "pagesize": (8.5, 11.0),
            "labelsize": (4.0, 1.5),
            "vertical_offsets": [1.0, 2.5, 4.0, 5.5, 7.0, 8.5],
            "horizontal_offsets": [0.15625, 4.34375],
            "margin": 0.075,
        },
        "7x2":
        {
            "name": "Letter-7x2",
            "description": '''Letter (8.5”×11”), 4”×1.333” labels, 14 per sheet''',
            "units": "inch",
            "pagesize": (8.5, 11.0),
            "labelsize": (4.0, 1.33333),
            "vertical_offsets": [0.83333, 2.16667, 3.50000, 4.83333, 6.16667, 7.50000, 8.83333],
            "horizontal_offsets": [0.15625, 4.34375],
            "margin": 0.06667,
        },
        "5x3":
        {
            "name": "Letter-5x3",
            "description": '''Letter (8.5”×11”), 2.625”×2” labels, 15 per sheet''',
            "units": "inch",
            "pagesize": (8.5, 11.0),
            "labelsize": (2.625, 2.0),
            "vertical_offsets": [0.5, 2.5, 4.5, 6.5, 8.5],
            "horizontal_offsets": [0.15625, 2.90625, 5.65625],
            "margin": 0.1,
        },
        "10x3":
        {
            "name": "Letter-10x3",
            "description": '''Letter (8.5”×11”), 2.625”×1” labels, 30 per sheet''',
            "template numbers": [],
            "units": "inch",
            "pagesize": (8.5, 11.0),
            "labelsize": (2.625, 1.0),
            "vertical_offsets": [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5],
            "horizontal_offsets": [0.15625, 2.90625, 5.65625],
            "margin": 0.05,
        },
    }
} #}}}

class PDFLabels:

    def __init__(self, parts_list=None):
        self._hwitems = list(set(parts_list)) or []

        self._label_types = {
            "qr": [],
            "bar": [],
        }

        self._images = {
            "qr": {},
            "bar": {},
        }

        self._part_data = {}

    @property
    def hwitems(self):
        return self._hwitems

    @hwitems.setter
    def hwitems(self, value):
        assert(isinstance(value, (list, tuple)))
        self._hwitems = list(value)

    def _get_image_async(self, code_type, pool, part_id):
        
        fn = {
            'qr': ra.get_hwitem_qrcode,
            'bar': ra.get_hwitem_barcode,
        }[code_type]

        crop_image_dim = _crop_dimensions[code_type]
        crop_bbox2 = _crop_bbox2[code_type]

        def async_fn(args, kwargs):
            resp = fn(*args, **kwargs)
            img_bytes = resp.content
            img_obj = PIL.Image.open(io.BytesIO(img_bytes))
            cropped_obj = img_obj.crop(crop_bbox2)
            return cropped_obj

        return pool.apply_async(async_fn, ((), {"part_id": part_id}))

    def _get_hwitem_async(self, pool, part_id):

        def async_fn(args, kwargs):
            data = ut.fetch_hwitems(*args, **kwargs)[part_id]
            
            cc = data["Item"]["country_code"]
            inst = data["Item"]["institution"]["id"]
            data["ExternalID"] = f'''{part_id}-{cc}{inst:03d}'''
            return data

        return pool.apply_async(async_fn, ((), {"part_id": part_id}))

    def _get_images(self):
        #{{{
        NUM_THREADS = 15
        save_session_kwargs = deepcopy(ra.session_kwargs)
        ra.session_kwargs["timeout"] = 16

        pool = mp.Pool(processes=NUM_THREADS) 

        fetch = lambda args, kwargs: ut.fetch_hwitems(*args, **kwargs)


        for part_id in self._hwitems:
            self._part_data[part_id] = self._get_hwitem_async(pool, part_id)
        
            for code_type in ('qr', 'bar'):
                if not self._label_types[code_type]:
                    continue
                self._images[code_type][part_id] = self._get_image_async(code_type, pool, part_id)

        pool.close()
        pool.join()

        for part_id in self._hwitems:
            self._part_data[part_id] = self._part_data[part_id].get()

            for code_type in ('qr', 'bar'):
                if not self._label_types[code_type]:
                    continue
                self._images[code_type][part_id] = self._images[code_type][part_id].get() 

        ra.session_kwargs = save_session_kwargs
        #}}}    

    def use_default_label_types(self):
        default_label_types = [
            ('qr', '4x3', 'A4'),
            ('bar', '11x4', 'A4'),
            
            ('qr', '2x2', 'letter'),
            ('qr', '3x2', 'letter'),
            #('qr', 'test', 'letter'),
            ('qr', '6x2', 'letter'),
            ('qr', '5x3', 'letter'),
            
            #('bar', '3x2', 'letter'),
            #('bar', '4x2', 'letter'),
            #('bar', '5x2', 'letter'),
            ('bar', '6x2', 'letter'),
            ('bar', '7x2', 'letter'),
            ('bar', '10x3', 'letter'),
        ]

        for args in default_label_types:
            self.add_label_type(*args)

    def add_label_type(self, code_type, template, page_size="letter"): 
        #{{{
        code_type = code_type.casefold()
        assert(code_type in ('qr', 'bar'))
        assert(page_size.casefold() in ('a4', 'letter'))
        page_size = {
            'a4': 'A4',
            'letter': 'letter',
        }[page_size.casefold()]

        if template in label_templates[page_size]:
            self._label_types[code_type].append(
                    label_templates[page_size][template])
        else:
            raise ValueError(f"Template ({page_size}, {template}) not defined")
        #}}}

    def generate_label_sheets(self, filename):
        #{{{
        if not _reportlab_available:
            print("Label generation unavailable. To enable label generation, install reportlab.\n"
                "Try: 'pip install reportlab'")
            return

        self._get_images()

        cvs = canvas.Canvas(filename)
        cvs.setTitle("HWDB Item Bar/QR Code Labels")
        cvs.setAuthor(f"HWDB Python Utility {Sisyphus.version}")

        def generate_intro_page(cvs, code_type, template):
            #{{{
            unit = {
                'mm': units.mm,
                'cm': units.cm,
                'pica': units.pica,
                'inch': units.inch,
            }[template['units']]

            page_width, page_height = [unit * x for x in template["pagesize"]]
            cvs.setPageSize( (page_width, page_height) )
            
            num_rows = len(template["vertical_offsets"])
            num_cols = len(template["horizontal_offsets"])
            items_per_page = num_rows * num_cols
            full_pages, leftovers = divmod(len(self._hwitems), items_per_page)
            num_pages = full_pages + (1 if leftovers else 0)
            margin = 0.5 * units.inch 


            logo_path = Sisyphus.get_path("resources/images/DUNE-logo.png")

            logo_pil = PIL.Image.open(logo_path)
            aspect_ratio = logo_pil.size[0]/logo_pil.size[1]
            image_width = page_width - 2 * margin
            image_height = image_width / aspect_ratio

            cvs.drawImage(
                    Sisyphus.get_path("resources/images/DUNE-logo.png"),
                    margin,
                    page_height - margin - image_height,
                    image_width,
                    image_height,
                    mask=[0, 0, 0, 0, 0, 0])

            cvs.setFont("Helvetica-Bold", 26)
            cvs.setFillColorRGB(0.486, 0.682, 0.835)
            cvs.setStrokeColorRGB(0.0, 0.0, 0.0)
            
            code_type_name = {
                'qr': 'QR',
                'bar': 'Bar'
            }[code_type]

            cvs.drawString(
                    margin, 
                    page_height - margin - 1.75 * units.inch,
                    f"Hardware Item {code_type_name} Code Labels")

            cvs.setFont("Helvetica", 14)
            cvs.drawString(
                    margin,
                    page_height - margin - 2.25 * units.inch,
                    f"Label Template: {template['description']}")

            template_page = cvs.getPageNumber() + 1

            text_object = cvs.beginText()
            text_object.setTextOrigin(
                        margin, 
                        page_height - margin - 3.25 * units.inch)
            text_object.setFillColorRGB(0.949, 0.408, 0.169)
            text_object.textLine(f"Print template on page {template_page} on normal "
                    "paper and check alignment with your label")
            text_object.textLine("sheet. You may need to disable "
                    "\"fit to page\" or adjust other settings to achieve")
            text_object.textLine("proper alignment.")

            
            first_page = template_page + 1
            last_page = first_page + num_pages - 1
            if first_page == last_page:
                text = f"Insert label sheet and print page {first_page} from this document."
            else:
                text = (f"Insert label sheet and print pages {first_page}-{last_page} "
                            "from this document.")

            text_object.textLine("")
            text_object.setFillColorRGB(0.486, 0.682, 0.835)
            text_object.textLine(text)
    
            cvs.drawText(text_object)

            cvs.showPage()

            generate_label_pages(cvs, code_type, template, label_outlines_only=True)

            #}}}


        def generate_label_pages(cvs, code_type, template, 
                        show_label_outlines=False, label_outlines_only=False):
            #{{{

            if label_outlines_only:
                show_label_outlines = True            

            template = deepcopy(template)
            
            unit = {
                'mm': units.mm,
                'cm': units.cm,
                'pica': units.pica,
                'inch': units.inch,
            }[template['units']]

            # Set the page size BEFORE deciding whether to rotate, because
            # if we rotate, we'll rotate into the correct footprint
            cvs.setPageSize( tuple(unit * d for d in template["pagesize"]) )                    

            
            labels_are_sideways = (template["labelsize"][1] > template["labelsize"][0])

            rotate = ( (code_type == "qr" and not labels_are_sideways)
                    or (code_type == "bar" and labels_are_sideways))
            #rotate = False

            if rotate:
                # swap the label dimensions
                label_width, label_height = template["labelsize"]
                template["labelsize"] = label_height, label_width
                
                # swap the offsets
                v_off, h_off = template["vertical_offsets"], template["horizontal_offsets"]
                template["horizontal_offsets"], template["vertical_offsets"] = v_off, h_off
                
                # swap the page dimensions
                # (even though the page dimensions have already been set,
                # these are still used for offset calculations)
                pw, ph = template["pagesize"]
                template["pagesize"] = ph, pw

            margin = template["margin"] 
            label_width, label_height = template["labelsize"]
            label_size = size(*template["labelsize"])
            available_width, available_height = [d - 2 * margin for d in template["labelsize"]]
            available_size = size(*[d - 2 * margin for d in template["labelsize"]])

            page_width, page_height = template["pagesize"]
            
            if code_type == 'qr':
                image_vert_alloc = 0.85
                caption_vert_alloc = 0.15
                font_scale = 0.45 # relative to the caption height
            else:
                image_vert_alloc = 0.67
                caption_vert_alloc = 0.33
                font_scale = 0.45
        
    
            num_rows = len(template["vertical_offsets"])
            num_cols = len(template["horizontal_offsets"])
            items_per_page = num_rows * num_cols
            full_pages, leftovers = divmod(len(self._hwitems), items_per_page)
            num_pages = full_pages + (1 if leftovers else 0)


            for page in range(num_pages):
                if label_outlines_only and page > 0:
                    break
                if rotate:
                    cvs.translate(unit * pw, 0.0)
                    cvs.rotate(90)

                for row, row_offset in enumerate(template["vertical_offsets"]):
                    for col, col_offset in enumerate(template["horizontal_offsets"]):

                        if rotate:
                            label_num = page * num_cols * num_rows + (num_cols-col-1) * num_rows + row
                        else:
                            label_num = page * num_rows * num_cols + row * num_cols + col

                        label_offset = coord(col_offset, page_height - row_offset - label_height)
                  
                        if show_label_outlines:
                            cvs.setLineWidth(1)
                            cvs.setStrokeColorRGB(0.80, 0.80, 0.80)
                            cvs.roundRect(
                                    *scaletuple(unit, bbox2(*label_offset, *label_size)),
                                    unit * min(label_size)/20,
                                    fill=0)                       


                        if _debug:
                            # Draw LABEL AREA bounding box
                            cvs.setLineWidth(0)
                            cvs.setStrokeColorRGB(0.80, 0.80, 0.80)
                            cvs.setFillColorRGB(0.90, 0.90, 0.90)
                            cvs.roundRect(
                                    *scaletuple(unit, bbox2(*label_offset, *label_size)),
                                    unit * min(label_size)/20,
                                    fill=1)                       

                        available_area_offset = addtuple(label_offset, (margin, margin))

                        if _debug:
                            # Draw AVAILABLE AREA bounding box
                            cvs.setLineWidth(0)
                            cvs.setStrokeColorRGB(0.80, 0.0, 0.0)
                            cvs.setFillColorRGB(0.90, 0.60, 0.60)
                            cvs.roundRect(
                                    *scaletuple(unit, bbox2(*available_area_offset, *available_size)),
                                    min(available_size)/20,
                                    fill=1)
                        
                        #
                        # Calculate the ALLOCATED size & offset
                        #
                        image_size = _crop_dimensions[code_type]
                        aspect_ratio = image_size.w / image_size.h

                        # assume the code+caption will take up the entire height, and
                        # calculate the width from the aspect_ratio
                        alloc_height = available_height
                        alloc_width = available_height * aspect_ratio * image_vert_alloc

                        # if the calculated width is more than the available width,
                        # reverse the assumptions above and calculate the height instead
                        if alloc_width > available_width:
                            alloc_width = available_width
                            alloc_height = available_width / (aspect_ratio * image_vert_alloc)
                        
                        alloc_size = size(alloc_width, alloc_height)
                        alloc_local_offset = size(
                                (available_size.w - alloc_size.w) / 2,
                                (available_size.h - alloc_size.h) / 2)
                        alloc_offset = addtuple(available_area_offset, alloc_local_offset)

                        if _debug:
                            # Draw ALLOCATED bounding box
                            cvs.setLineWidth(0)
                            cvs.setStrokeColorRGB(0.0, 0.8, 0.8)
                            cvs.setFillColorRGB(0.8, 1.0, 1.0)
                            cvs.roundRect(
                                    *scaletuple(unit, bbox2(*alloc_offset, *alloc_size)),
                                    unit * 1/32,
                                    fill=1)
                        
                        image_height = alloc_size.h * image_vert_alloc
                        image_width = alloc_size.w

                        image_size = size(alloc_size.w, alloc_size.h * image_vert_alloc)

                        image_x_offset = 0.5 * (alloc_size.w - image_size.w)
                        image_y_offset = 0.5 * (alloc_size.h - image_size.h)
                        
                        image_local_offset = coord(
                                    0.5 * (alloc_size.w - image_size.w),
                                    (alloc_size.h - image_size.h))
                        image_offset = addtuple(alloc_offset, image_local_offset)

                        caption_height = alloc_size.h * caption_vert_alloc

                        caption_size = size(image_size.w, alloc_size.h * caption_vert_alloc)
                        font_size = caption_size.h * font_scale
                        
                        caption_bottom_center_offset = addtuple(
                                    alloc_offset, size(caption_size.w/2, 0))
                        caption_top_center_offset = addtuple(
                                    alloc_offset, 
                                    size(caption_size.w/2, caption_size.h-font_size/2))
                        caption_line_1_offset = addtuple(
                                    alloc_offset, 
                                    size(caption_size.w/2, 0.80 * caption_size.h-font_size/2))
                        caption_line_2_offset = addtuple(
                                    alloc_offset, 
                                    size(caption_size.w/2, 0.30 * caption_size.h-font_size/2))
                        
                        if _debug:
                            # Draw CAPTION AREA bounding box
                            cvs.setLineWidth(0)
                            cvs.setStrokeColorRGB(0.60, 0.60, 0.0)
                            cvs.setFillColorRGB(1.0, 1.0, 0.60)
                            cvs.roundRect(
                                    *scaletuple(unit, bbox2(*alloc_offset, *caption_size)),
                                    min(caption_size)/20,
                                    fill=1)

        
                        if label_num >= len(self._hwitems) or label_outlines_only:
                            continue


                        ### Canvas.DrawImage() appears to be broken and 
                        ### does not accept a PIL image or a bytes object
                        ### as advertised, so to get around it, we will
                        ### write it to a temporary file and use the file
                        ### name instead.
                        part_id = self._hwitems[label_num]
                        image_pil = self._images[code_type][part_id]
                        with tempfile.NamedTemporaryFile() as tf:
                            #tf.write(image_bytes)
                            image_pil.save(tf, 'png')
                            #tf.seek(0)                        
                            
                            cvs.drawImage(tf.name,
                                    *scaletuple(unit, bbox2(*image_offset, *image_size)),
                                    mask = [0xEE, 0xFF, 0xEE, 0xFF, 0xEE, 0xFF]
                                    )


                        if code_type == 'qr':
                            part_id_str = part_id
                        else:
                            part_id_str = self._part_data[part_id]["ExternalID"]
                        part_name = self._part_data[part_id]["Item"]["component_type"]["name"]

                        cvs.setFont("Helvetica-Bold", unit * font_size)
                        cvs.setLineWidth(1)
                        cvs.setFillColorRGB(0.0, 0.0, 0.0)
                        cvs.setStrokeColorRGB(0.0, 0.0, 0.0)
                            
                        cvs.drawCentredString(
                                *scaletuple(unit, caption_line_1_offset),
                                part_id_str)
                        cvs.drawCentredString(
                                *scaletuple(unit, caption_line_2_offset),
                                part_name)


                cvs.showPage()
            #}}}


        for code_type in ('bar', 'qr'):
            for template in self._label_types[code_type]:
                generate_intro_page(cvs, code_type, template)
                generate_label_pages(cvs, code_type, template, False)

        cvs.save()
        #}}}
    
