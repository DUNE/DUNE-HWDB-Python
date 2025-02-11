#!/usr/bin/env python
# -*- coding: utf-8 -*-

contents = \
{
    "page sizes": {},
    "label templates": {},
    "layouts": {
        "Test Layout 1": {
            "label template": "Letter-2x3-Avery",
            "debug": True,
            "elements": [
                {
                    "element type": "qr",
                    "alignment": "top-left",
                    "anchor": ["10%", "10%"],
                    "size": ["80%", "40%"],
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
            ]
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
        "Z00100300012": [
            "Test Layout 1", 
            "Test Layout 2",
            "Test Layout 3",
            "Test Layout 4",
            "Test Layout 5",
            "Test Layout 6",
        ],
    }
}
