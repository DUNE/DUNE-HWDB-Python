#!/usr/bin/env python
# -*- coding: utf-8 -*-

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)

import Sisyphus
from Sisyphus import RestApiV1 as ra
from Sisyphus.RestApiV1 import Utilities as ut

import json
import PIL.Image
import io
import sys
import re
from copy import deepcopy
import multiprocessing.dummy as mp # multiprocessing interface, but uses threads instead
import tempfile

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib import units
    _reportlab_available = True

except ModuleNotFoundError:
    _reportlab_available = False


class PDFLabels:
    def __init__(self, parts_list=None, label_set=None):
        parts_list = parts_list or []

        self.parts_list = list(sorted(list(set(parts_list)))) or []
        self._label_set = label_set
        self.label_jobs = {}
    
        self._load_configuration()
        self._get_hwitems()
        self._sort_jobs()


    def _sort_jobs(self):
        #{{{
        jobs = self.label_jobs
        label_templates = self.config["label templates"]
        
        for part_id, part_data in self.parts_data.items():

            part_type_id = part_data["part_type_id"]
            part_name = part_data["part_name"]

            if self._label_set is not None:
                label_set = self.config["label sets"]["default"]
            elif part_type_id in self.config["label sets"]:
                label_set = self.config["label sets"][part_type_id]
            else:
                label_set = self.config["label sets"]["default"]
             
            for layout_name in label_set:
                layout_def = self.config["layouts"][layout_name]
                template_name = layout_def["label template"]
                page_size = label_templates[template_name]["page size"]

                jobs.setdefault(page_size, {}) \
                    .setdefault(template_name, {}) \
                    .setdefault(layout_name, []) \
                    .append(part_id)
        #}}}


    def _load_configuration(self):
        #{{{
        self.default_config = config.load_additional_config(
                                        "default_labels.py", recopy_on_error=True)
        try:
            self.custom_config = config.load_additional_config(
                                        "custom_labels.py", recopy_on_error=False)
        except Exception as ex:
            logger.error(ex)
            print("cannot load custom configuration file. see logs for details.")
            self.custom_config = {}

        #print(f"default: {json.dumps(self.default_config, indent=4)}")
        #print(f"custom: {json.dumps(self.custom_config, indent=4)}")

        self.config = deepcopy(self.default_config)

        for node_name, node_contents in self.custom_config.items():
            self.config.setdefault(node_name, {})
            for child_node_name, child_node_contents in node_contents.items():
                if child_node_contents is None:
                    if child_node_name in self.config[node_name]:
                        del self.config[node_name][child_node_name]
                else:
                    self.config[node_name][child_node_name] = child_node_contents

        #print(f"merged: {json.dumps(self.config, indent=4)}")
        #}}}

    def _get_hwitems(self):
        #{{{
        # get the part names and qr/bar images for each part in the parts_list

        NUM_THREADS = 15
        pool = mp.Pool(processes=NUM_THREADS)

        def get_hwitem_async(part_id):
            def async_fn(args, kwargs):
                data = ut.fetch_hwitems(*args, **kwargs)[part_id]
                cc = data["Item"]["country_code"]
                inst = data["Item"]["institution"]["id"]

                ext_id = f'''{part_id}-{cc}{inst:03d}'''

                retval = {
                    "part_id": part_id,
                    "ext_id": ext_id,
                    "part_type_id": data["Item"]["component_type"]["part_type_id"],
                    "part_name": data["Item"]["component_type"]["name"],
                }

                return retval
            return pool.apply_async(async_fn, ((), {"part_id": part_id}))

        def get_qr_async(part_id):
            crop_bbox = (40, 40, 410, 410)
            def async_fn(args, kwargs):
                resp = ra.get_hwitem_qrcode(*args, **kwargs)
                img_bytes = resp.content
                img_obj = PIL.Image.open(io.BytesIO(img_bytes))
                cropped_obj = img_obj.crop(crop_bbox)
                return cropped_obj
            return pool.apply_async(async_fn, ((), {"part_id": part_id}))

        def get_bar_async(part_id):
            crop_bbox = (30, 11, 658, 189)
            def async_fn(args, kwargs):
                resp = ra.get_hwitem_barcode(*args, **kwargs)
                img_bytes = resp.content
                img_obj = PIL.Image.open(io.BytesIO(img_bytes))
                cropped_obj = img_obj.crop(crop_bbox)
                return cropped_obj
            return pool.apply_async(async_fn, ((), {"part_id": part_id}))

        parts_data_futures = {}
        qr_data_futures = {}
        bar_data_futures = {}

        for part_id in self.parts_list:
            parts_data_futures[part_id] = get_hwitem_async(part_id)
            qr_data_futures[part_id] = get_qr_async(part_id)
            bar_data_futures[part_id] = get_bar_async(part_id)

        pool.close()
        pool.join()

        self.parts_data = {}


        for part_id in self.parts_list:
            self.parts_data[part_id] = parts_data_futures[part_id].get()
            self.parts_data[part_id]['qr'] = qr_data_futures[part_id].get()
            self.parts_data[part_id]['bar'] = bar_data_futures[part_id].get()
        #}}}

    def generate_label_sheets(self, filename):
        #{{{
        if not _reportlab_available:
            print("Label generation unavailable. To enable label generation, install reportlab.\n"
                "Try: 'pip install reportlab'")
            return
       
        self.cvs = cvs = canvas.Canvas(filename)
        cvs.setTitle("HWDB Item Bar/QR Code Labels")
        cvs.setAuthor(f"HWDB Python Utility {Sisyphus.version}")

        for page_size, page_size_jobs in self.label_jobs.items():
            for label_template, label_template_jobs in page_size_jobs.items():
                self._handle_template_set(page_size, label_template, label_template_jobs) 
 
        cvs.save()
        #}}}

    def _handle_template_set(self, page_size_name, label_template_name, label_template_jobs):
        #{{{
        page_size = self.config["page sizes"][page_size_name]
        page_size["name"] = page_size_name

        label_template = deepcopy(self.config["label templates"][label_template_name])
        label_template["name"] = label_template_name
        label_template["size"] = page_size["size"]
        label_template["units"] = {
            'mm': units.mm,
            'cm': units.cm,
            'pica': units.pica,
            'inch': units.inch }[page_size["units"]]
        

        labels_per_page = len(label_template["horizontal offsets"]) \
                    * len(label_template["vertical offsets"])
        label_template["labels_per_page"] = labels_per_page

        num_labels = sum([len(L) for L in label_template_jobs.values()])
        
        full_pages, leftovers = divmod(num_labels, labels_per_page)
        num_pages = full_pages + (1 if leftovers else 0)

        self._generate_intro_page(label_template, num_pages)
        self._generate_template_page(label_template)
        self._generate_label_pages(label_template, label_template_jobs)
        #}}}

    def _generate_intro_page(self, label_template, num_pages):
        #{{{
        cvs = self.cvs
        unit = label_template['units']
        page_width, page_height = [unit * x for x in label_template["size"]]
        cvs.setPageSize((page_width, page_height))


        margin = 0.5 * units.inch
        logo_path = Sisyphus.get_path("resources/images/DUNE-logo.png")
        logo_pil = PIL.Image.open(logo_path)
        aspect_ratio = logo_pil.size[0]/logo_pil.size[1]
        image_width = page_width - 2 * margin
        image_height = image_width / aspect_ratio

        cvs.drawImage(
                logo_path,
                margin,
                page_height - margin - image_height,
                image_width,
                image_height,
                mask=[0, 0, 0, 0, 0, 0])

        cvs.setFont("Helvetica-Bold", 26)
        cvs.setFillColorRGB(0.486, 0.682, 0.835)
        cvs.setStrokeColorRGB(0.0, 0.0, 0.0)

        cvs.drawString(
                margin,
                page_height - margin - 1.75 * units.inch,
                f"Hardware Item QR/bar Code Labels")

        cvs.setFont("Helvetica", 14)
        cvs.drawString(
                margin,
                page_height - margin - 2.25 * units.inch,
                f"Label Template: {label_template['description']}")

        template_page = cvs.getPageNumber() + 1
        first_page = template_page + 1
        last_page = first_page + num_pages - 1

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
        #}}}

    def _generate_template_page(self, label_template):
        #{{{
        cvs = self.cvs
        unit = label_template['units']
        page_width, page_height = [unit * x for x in label_template["size"]]

        label_width, label_height = [unit * x for x in label_template["label size"]]
        rounding = unit * label_template.get("rounding", 0)

        h_offsets = [unit * x for x in label_template["horizontal offsets"]]
        v_offsets = [unit * x for x in label_template["vertical offsets"]]

        cvs.setPageSize((page_width, page_height))

        for v_offset in v_offsets:
            for h_offset in h_offsets:
                
                cvs.setLineWidth(1)
                cvs.setStrokeColorRGB(0.80, 0.80, 0.80) 
                cvs.setFillColorRGB(0.90, 0.90, 0.90)
                cvs.roundRect(
                    h_offset,
                    page_height - v_offset - label_height,
                    label_width,
                    label_height,
                    rounding)
        cvs.showPage()
        #}}}

    def _generate_label_pages(self, label_template, label_template_jobs):
        #{{{
        cvs = self.cvs
        unit = label_template['units']
        page_width, page_height = [unit * x for x in label_template["size"]]
        label_width, label_height = [unit * x for x in label_template["label size"]]                        
        rounding = unit * label_template.get("rounding", 0)

        h_offsets = [unit * x for x in label_template["horizontal offsets"]]
        v_offsets = [unit * x for x in label_template["vertical offsets"]]

        position_index = []
        for v_offset in v_offsets:
            for h_offset in h_offsets:
                position_index.append( (h_offset, v_offset) )

        cvs.setPageSize((page_width, page_height))

        scan_codes = []

        for layout_name, part_ids in label_template_jobs.items():
            for part_id in part_ids:
                scan_codes.append({
                        "part_id": part_id,
                        "layout_name": layout_name
                })



        full_pages, leftovers = divmod(len(scan_codes), label_template["labels_per_page"])
        num_pages = full_pages + (1 if leftovers else 0)

        for page_num in range(num_pages):
            for pos_index, offset in enumerate(position_index):
                total_index = page_num * label_template["labels_per_page"] + pos_index
                label_index = total_index
                if total_index >= len(scan_codes):
                    label_index = None

                if label_index is not None:
                    code_data = scan_codes[label_index]
                else:
                    code_data = None


                cvs.saveState()
                cvs.translate(offset[0], page_height-offset[1])
                self._generate_label(label_template, offset, code_data)
                cvs.restoreState()


                if (total_index+1) % label_template["labels_per_page"] == 0:
                    cvs.showPage()
        #}}}            
    
    def _generate_label(self, label_template, offset, code_data):
        #{{{
        def convert_percent(s, size):
            #{{{
            if type(s) is str:
                if s[-1] == "%":
                    return 0.01 * float(s[:-1]) * size
                else:
                    return float(s)
            else:
                return s
            #}}}

        def draw_marker(x, y, color=(0.5, 0.5, 0.8), r=2.5, text="marker"):
            #{{{
            # for debugging purposes
            cvs.saveState()
            cvs.setLineWidth(2)
            cvs.setStrokeColorRGB(*color)
            cvs.ellipse(x-r * units.mm, y-r * units.mm, x+r * units.mm, y+r*units.mm)
            cvs.setFillColorRGB(*color)
            cvs.setStrokeColorRGB(*color)
            cvs.drawString(x, y, text)
            cvs.restoreState()
            #}}}
        #def draw_image(img, x, y, w, h, par, align, debug):
        def draw_element(
                x, y, w, h, *,
                img = None,
                text = None,
                font_size = 10,
                preserve_aspect = False, 
                align = 'top_left', 
                debug = False,
                rotate = 0):
            #{{{
            
            if text is not None:
                h = font_size

            ww, hh = w, h
            if img is not None:
                img_w, img_h = img.size
            
                if preserve_aspect:
                    img_AR = img_w / img_h
                    alloc_AR = w / h
                    AR_R = alloc_AR / img_AR
                    if AR_R > 1:
                        ww = w/AR_R
                    else:
                        hh = h*AR_R
           
            if align == 'center':
                align = 'center-center'
            valign, halign = align.split('-') 
            if valign == 'top':
                v_offset = 0
                vv_offset = 0
            elif valign == 'center':
                v_offset = h/2
                vv_offset = hh/2
            elif valign == 'bottom':
                v_offset = h
                vv_offset = h

            if halign == 'left':
                h_offset = 0
                hh_offset = 0
            elif halign == 'center':
                h_offset = w/2
                hh_offset = ww/2
            elif halign == 'right':
                h_offset = w
                hh_offset = ww

            


            #print(f"x: {x}, y: {y}, w: {w}, h: {h}")
            #print(f"label: {label_width} x {label_height}")
            #print(f"align: {align}")
            #print(f"anchor: {h_offset}, {v_offset}")

            cvs.saveState()

            cvs.translate(x, -y)
            cvs.rotate(rotate)


            if img is not None:
                with tempfile.NamedTemporaryFile() as tf:
                    img.save(tf, 'png')
                    cvs.drawImage(
                            tf.name,
                            -hh_offset,
                            -hh + vv_offset,
                            ww,
                            hh)



            if text is not None:
                cvs.saveState()
                cvs.setFillColorRGB(0, 0, 0)
                cvs.setStrokeColorRGB(0, 0, 0)
                cvs.setFont("Helvetica-Bold", font_size*1.35)
                if halign == "left":
                    cvs.drawString(0, -font_size+v_offset, text)
                elif halign == "center":
                    cvs.drawCentredString(0, -font_size+v_offset, text)
                elif halign == "right":
                    cvs.drawRightString(0, -font_size+v_offset, text)
                

                #text_object = cvs.beginText()
                #text_object.setTextOrigin(0, 0)
                #text_object.textLine("above")
                #text_object.textLine(text)
                #text_object.textLine("below")
                #cvs.drawText(text_object)
                


                cvs.restoreState()






            if debug and img is not None:
                cvs.rect(
                    -h_offset,
                    +v_offset-h,
                    w,
                    h)
            
                if preserve_aspect:
                    cvs.rect(
                        -hh_offset,
                        +vv_offset - hh,
                        ww,
                        hh)

            if debug:
                draw_marker(0, 0, color=(0.8, 0.3, 0.3), r=2.0, text="anchor")
            
            cvs.restoreState()
            #}}}

        cvs = self.cvs

        unit = label_template['units']
        page_width, page_height = [unit * x for x in label_template["size"]]
        label_width, label_height = [unit * x for x in label_template["label size"]]
        rounding = unit * label_template.get("rounding", 0)

        # h_offset, v_offset = offset
        h_offset, v_offset = 0, 0

        debug = False
        if code_data is not None:
            layout_def = self.config['layouts'][code_data['layout_name']]
            debug = layout_def.get('debug', False)
            part_data = self.parts_data[code_data['part_id']]

        if debug or label_template.get("draw outline", False) == True:
            cvs.setLineWidth(1)
            cvs.setStrokeColorRGB(0.80, 0.80, 0.80) 
            cvs.setFillColorRGB(0.90, 0.90, 0.90)
            cvs.roundRect(
                #h_offset,
                #page_height - v_offset - label_height,
                0, -label_height,
                label_width,
                label_height,
                rounding)
            
        if code_data is None:
            return

        part_data = self.parts_data[code_data['part_id']]


        orientation = layout_def.get("orientation", "portrait")

        cvs.saveState()
        if orientation == "landscape":
            cvs.translate(0, -label_height)
            cvs.rotate(90)
            label_width, label_height = label_height, label_width
            


        if debug:
            draw_marker(0, 0, color=(0.5, 0.5, 0.8), r=2.5, text="label origin")

        for element in layout_def["elements"]:

            anchor_h, anchor_v = element.get("anchor", [0, 0])
            size_h, size_v = element.get("size", ["100%", "100%"])
            preserve_aspect = element.get("preserve aspect ratio", False)
            align = element.get("alignment", "top-left")
            font_size = element.get("font size", 10)
            rotate = element.get("rotate", 0)

            anchor_h = convert_percent(anchor_h, label_width)
            anchor_v = convert_percent(anchor_v, label_height)
            size_h = convert_percent(size_h, label_width)
            size_v = convert_percent(size_v, label_height)
            font_size = convert_percent(font_size, label_height)           
 
            element.setdefault("element type", None)
            if element["element type"] in ("part id", "external id", "part name"):

                key = {
                    "part id": "part_id",
                    "external id": "ext_id",
                    "part name": "part_name"
                }[element["element type"]]         


                text = part_data[key]

                draw_element(
                    anchor_h, anchor_v,
                    size_h, size_v,
                    text = text,
                    font_size = font_size,
                    align = align,
                    debug = debug,
                    rotate = rotate)

            elif element["element type"] in ("qr", "bar"):
                draw_element(
                    anchor_h, anchor_v,
                    size_h, size_v,
                    img = part_data[element['element type']],
                    preserve_aspect = preserve_aspect,
                    align = align,
                    debug = debug,
                    rotate = rotate)

        cvs.restoreState()
        #}}}


if __name__ == '__main__':

    parts_list = sys.argv[1:]

    pdf_labels = PDFLabels(parts_list)
    pdf_labels.generate_label_sheets("label_test.pdf")












