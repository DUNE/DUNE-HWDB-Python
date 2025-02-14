#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This is a sample custom_labels.py file. The contents of this file is merged
# with the default_labels.py file to produce a single label configuration.

# Note that since this is a Python file, you can execute it in Python to check
# if it is syntactically valid!

contents = \
{
    "page sizes": {
        # Use this node to define other page sizes if you need more sizes
        # than A4 and Letter, which are already defined in default_labels.py
        # By convention, we've been defining these in "portrait" orientation.
        # If you wish to use a page in "landscape" orientation, you can 
        # specify that in "layouts". You do not need to create a new page
        # size definition for it.

        "A5": {
            # No label sheets are currently defined using this size. It is 
            # provided only for the purpose of illustration.
            
            # "units" may be "mm", "cm", "inch", or "pica".
            "units": "mm",

            # "size": (width, height), in the preferred units
            "size": (148.5, 210)
        }
    },

    "label templates": {
        # Use this node to define the dimensions of label sheets. You may
        # name these however you like, but the convention we've been using
        # is <page size>-<columns>x<rows>-<brand name>.

        "Letter-2x7-Avery":
        {
            # "description" will be displayed on the first page of the pdf
            # label sheet for the set of labels using that label template
            "description": '''Letter (8.5”×11”), 4”×1.333” labels, 14 per sheet''',
            
            # "page size" is required. The units defined for that page size
            # will be used throughout the template definition.
            "page size": "Letter",

            # "label size": (width, height), all labels must be the same size.
            # If sheets have multiple sizes, the software will need to be updated
            # to accommodate.
            "label size": (4.0, 1.33333),
            
            
            # "horizontal offsets": (list of offsets), offsets from the left
            # edge of the page to the left edge of each label.
            "horizontal offsets": (0.15625, 4.34375),
            
            # "vertical offsets": (list of offsets), offsets from the top 
            # edge of the page to the top edge of each label.
            "vertical offsets": (0.833, 2.167, 3.500, 4.833, 6.167, 7.500, 8.833),
            
            # "rounding" defines the radius of curvature for the rounding at
            # the corners of the labels. It is only used when drawing the
            # outlines of labels. It does not affect or interfere with the 
            # printing of the contents of the label.
            "rounding": 0.125,
            
            # "draw outline" determines if the outline should be drawn for 
            # labels after the alignment sheet. (Outlines will always be 
            # drawn on the alignment sheet regardless.) Typically, you will
            # want this value to be False unless you troubleshooting.
            "draw outline": False,
        },
    },

    "layouts": {
        # Use this node to define how you want the utility to print contents
        # onto each label on a sheet defined in "templates". You may define as
        # many layouts as you wish for a given template.

        # The samples here all use the "Letter-2x3-Avery" template defined
        # in default_labels.py

        "Test Layout 1": {

            # "label template" must point to one of the label templates defined
            # in this file or in default_labels.py
            "label template": "Letter-2x3-Avery",

            # "orientation" is optional and will default to "portrait" if not
            # provided. If the orientation is "portrait," the label size will
            # be the same as defined in "templates," and the upper left corner
            # of the label will correspond to the upper left corner of the
            # label on the sheet. If the orientation is "landscape," the label
            # dimensions will be swapped, and the coordinate system will be
            # rotated 90 degrees counterclockwise.
            "orientation": "portrait",

            # "elements" represents the objects to be printed on each label.
            #
            # Each element must have an "element type".
            #     The available element types are:
            #         "qr": a QR code encoding a link to the HWDB web page
            #               for the part
            #         "bar": a bar code encoding the External ID of the part
            #         "part id": the Part ID of the part, 
            #                    e.g., "Z00100300001-00001"
            #         "external id": the External ID of the part, e.g., 
            #                        "Z00100300001-00001-US186"
            #         "part name": the name in the HWDB for the associated
            #                      part type
            #         "text": free-form text
            #
            # Elements should have an "anchor" position on the label. This 
            # may be given in absolute units, or as a percentage of the 
            # label's width or height. (If given as a percentage, the value
            # must be given as a string.)
            #
            # Beware that there's nothing preventing you from positioning an 
            # element outsize the bounds of the label!
            #
            # Elements should have an "alignment" describing what part of 
            # the element is anchored at the "anchor" point. E.g., if the 
            # alignment is "center", then the center of the element will be
            # located at the anchor point. If "alignment" is not provided, it
            # will default to "top-left"
            #     Valid alignments are:
            #         top-left     top-center     top-right
            #         center-left  center         center-right
            #         bottom-left  bottom-center  bottom-right
            #
            # "qr" and "bar" elements should have a "size" defining the 
            # size of these elements on the label. These may be given in
            # absolute units or as percentages of the height or width of 
            # the label. Text-type elements will ignore "size"
            #
            # "qr" and "bar" elements may define "preserve aspect ratio"
            # as True in order to keep their original aspect ratios. Text-type
            # elements will ignore "preserve aspect ratio".
            #
            # Text-type elements ("part id", "external id", "part name", and
            # "text") should define "font size". If "font size" is given as
            # a percentage, it is the percentage of the label's height.
            #
            # Text-type elements may define "font face". The default
            # is "Helvetica-Bold". If the utility cannot find the font given,
            # it reverts to "Helvetica-Bold" and a warning is logged.
            #     The available fonts are:
            #         Courier
            #         Courier-Bold
            #         Courier-BoldOblique
            #         Courier-Oblique
            #         Helvetica
            #         Helvetica-Bold
            #         Helvetica-BoldOblique
            #         Helvetica-Oblique
            #         Symbol
            #         Times-Bold
            #         Times-BoldItalic
            #         Times-Italic
            #         Times-Roman
            #         ZapfDingbats
            #
            # All elements may define "rotate". This will rotate the object
            # by the number of degrees indicated, counterclockwise around the
            # anchor point. (Note that if the size is defined in percentages,
            # it is still the percentages of the width or height of the label
            # without factoring in any rotations.)

            "elements": [
                {
                    "element type": "qr",
                    "alignment": "top-left",
                    "anchor": ["10%", "10%"],
                    "size": ["40%", "30%"],
                    "preserve aspect ratio": True,
                },
                {
                    "element type": "bar",
                    "alignment": "top-left",
                    "anchor": ["60%", "10%"],
                    "size": ["30%", "30%"],
                    "preserve aspect ratio": True,
                },
                {
                    "element type": "part id",
                    "alignment": "top-left",
                    "anchor": ["10%", "55%"],
                    "font size": "5%",
                },
                {
                    "element type": "external id",
                    "alignment": "top-left",
                    "anchor": ["10%", "65%"],
                    "font size": "5%",
                },
                {
                    "element type": "part name",
                    "alignment": "top-left",
                    "anchor": ["10%", "75%"],
                    "font size": "5%",
                },
                {
                    "element type": "text",
                    "text": "Have a nice day!",
                    "alignment": "top-left",
                    "anchor": ["10%", "85%"],
                    "font size": "5%",
                },
            ],

            # set "debug" to True if you want to see the bounding boxes for
            # images and the anchor points for all elements
            "debug": True
        },

        "Test Layout 2": {
            "label template": "Letter-2x3-Avery",
            "debug": True,
            "elements": [
                {
                    "element type": "qr",
                    "alignment": "center",
                    "anchor": ["50%", "30%"],
                    "size": ["80%", "40%"],
                    "preserve aspect ratio": True,
                },
                {
                    "element type": "part id",
                    "alignment": "top-center",
                    "anchor": ["50%", "55%"],
                    "font size": "5%",
                },
                {
                    "element type": "part id",
                    "alignment": "center",
                    "anchor": ["50%", "65%"],
                    "font size": "5%",
                },
                {
                    "element type": "part id",
                    "alignment": "bottom-left",
                    "anchor": ["10%", "75%"],
                    "font size": "5%",
                },
                {
                    "element type": "part id",
                    "alignment": "bottom-right",
                    "anchor": ["90%", "85%"],
                    "font size": "5%",
                },
            ]
        },

        "Test Layout 3": {
            "label template": "Letter-2x3-Avery",
            "debug": True,
            "elements": [
                {
                    "element type": "qr",
                    "alignment": "bottom-right",
                    "anchor": ["90%", "50%"],
                    "size": ["80%", "40%"],
                    "preserve aspect ratio": True,
                },
            ]
        },

        "Test Layout 4": {
            "label template": "Letter-2x3-Avery",
            "debug": True,
            "elements": [
                {
                    "element type": "bar",
                    "alignment": "center-left",
                    "anchor": ["10%", "30%"],
                    "size": ["80%", "40%"],
                    "preserve aspect ratio": True,
                },
                {
                    "element type": "text",
                    "text": "Courier",
                    "alignment": "top-left",
                    "anchor": ["10%", "55%"],
                    "font size": "3.5%",
                    "font face": "Courier",
                },
                {
                    "element type": "text",
                    "text": "Courier-Bold",
                    "alignment": "top-left",
                    "anchor": ["50%", "55%"],
                    "font size": "3.5%",
                    "font face": "Courier-Bold",
                },
                {
                    "element type": "text",
                    "text": "Courier-Oblique",
                    "alignment": "top-left",
                    "anchor": ["10%", "63%"],
                    "font size": "3.5%",
                    "font face": "Courier-Oblique",
                },
                {
                    "element type": "text",
                    "text": "Courier-BoldOblique",
                    "alignment": "top-left",
                    "anchor": ["50%", "63%"],
                    "font size": "3.5%",
                    "font face": "Courier-BoldOblique",
                },
                {
                    "element type": "text",
                    "text": "Times-Roman",
                    "alignment": "top-left",
                    "anchor": ["10%", "71%"],
                    "font size": "3.5%",
                    "font face": "Times-Roman",
                },
                {
                    "element type": "text",
                    "text": "Times-Bold",
                    "alignment": "top-left",
                    "anchor": ["50%", "71%"],
                    "font size": "3.5%",
                    "font face": "Times-Bold",
                },
                {
                    "element type": "text",
                    "text": "Times-Italic",
                    "alignment": "top-left",
                    "anchor": ["10%", "79%"],
                    "font size": "3.5%",
                    "font face": "Times-Italic",
                },
                {
                    "element type": "text",
                    "text": "Times-BoldItalic",
                    "alignment": "top-left",
                    "anchor": ["50%", "79%"],
                    "font size": "3.5%",
                    "font face": "Times-BoldItalic",
                },
            ]
        },

        "Test Layout 5": {
            "label template": "Letter-2x3-Avery",
            "debug": True,
            "elements": [
                {
                    "element type": "qr",
                    "alignment": "center",
                    "anchor": ["30%", "50%"],
                    "size": ["80%", "40%"],
                    "preserve aspect ratio": True,
                    "rotate": 90,
                    
                },
                {
                    "element type": "text",
                    "font-size": "3.5%",
                    "anchor": ["50%", "10%"],
                    "text": "unrotated",
                },
                {
                    "element type": "text",
                    "font-size": "3.5%",
                    "anchor": ["50%", "30%"],
                    "text": "rotated 30 degrees",
                    "rotate": 30,
                },
            ]
        },

        "Test Layout 6": {
            "label template": "Letter-2x3-Avery",
            "orientation": "landscape",
            "debug": True,
            "elements": [
                {
                    "element type": "qr",
                    "alignment": "top-center",
                    "anchor": ["50%", "4%"],
                    "size": ["90%", "90%"],
                    "preserve aspect ratio": True,
                },
                {
                    "element type": "part id",
                    "alignment": "top-center",
                    "anchor": ["50%", "83%"],
                    "font size": "5%",
                    "preserve aspect ratio": True,
                },
                {
                    "element type": "part name",
                    "alignment": "top-center",
                    "anchor": ["50%", "90%"],
                    "font size": "5%",
                    "preserve aspect ratio": True,
                },
            ]
        },
    },

    "label sets": {
        # Label Sets define which layouts should be used with each part type.
        # To use a set of layouts for all part types, use 'default' as the 
        # part name. (This will override the 'default' already set in 
        # default_labels.py

        # To test the layouts in this file, try:
        #   hwdb-labels Z00100300001-00001
        #
        "Z00100300001": [
            "Test Layout 1", 
            "Test Layout 2",
            "Test Layout 3",
            "Test Layout 4",
            "Test Layout 5",
            "Test Layout 6",
        ],
    }
}
