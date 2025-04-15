#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy

Utilities for dealing with fonts

This is primarily needed to guess how wide to make columns in Excel.
"""

import Sisyphus

import os, sys
from PIL import ImageFont


known_fonts = \
{
#{{{
    "_subdir": "resources/fonts",
    "Calibri":
    {
        "_subdir": "calibri-font-family",
        "_file": "calibri-regular.ttf",
        "Bold":
        {
            "_subdir": ".",
            "_file": "calibri-bold.ttf",
            "Italic":
            {
                "_file": "calibri-bold-italic.ttf",
            },
        },
        "Italic":
        {
            "_file": "calibri-italic.ttf",
        },
    },
    "Liberation":
    {
        "_subdir": "liberation-fonts-ttf-2.1.5",
        "Mono":
        {
            "_subdir": ".",
            "_file": "LiberationMono-Regular.ttf",
            "Bold": 
            {
                "_subdir": ".",
                "_file": "LiberationMono-Bold.ttf",
                "Italic":
                {
                    "_file": "LiberationMono-BoldItalic.ttf",
                },
            },
            "Italic": 
            {
                "_file": "LiberationMono-Italic.ttf",
            },
        },
        "Sans":
        {
            "_subdir": ".",
            "_file": "LiberationSans-Regular.ttf",
            "Bold":
            {
                "_subdir": ".",
                "_file": "LiberationSans-Bold.ttf",
                "Italic":
                {
                    "_file": "LiberationSans-BoldItalic.ttf",
                },
            },
            "Italic":
            {
                "_file": "LiberationSans-Italic.ttf",
            },
        },
        "Serif":
        {
            "_subdir": ".",
            "_file": "LiberationSerif-Regular.ttf",
            "Bold":
            {
                "_subdir": ".",
                "_file": "LiberationSerif-Bold.ttf",
                "Italic":
                {
                    "_file": "LiberationSerif-BoldItalic.ttf",
                },
            },
            "Italic":
            {
                "_file": "LiberationSerif-Italic.ttf",
            },
        },
    },
#}}}
}

def list_fonts(fonts=known_fonts, name="", subdir=Sisyphus.project_root):
    if "_subdir" in fonts.keys():
        subdir = os.path.join(subdir, fonts["_subdir"])
    if "_file" in fonts.keys():
        yield name, os.path.realpath(os.path.join(subdir, fonts["_file"]))
    for key, value in fonts.items():
        if key.startswith("_"):
            continue
        yield from list_fonts(fonts[key], " ".join([name, key]).strip(), subdir)


def get_font(name, size):
    """Return a PIL.ImageFont for the name and font size

    This can then be used to calculate the width of text through
    font.getbbox(text) or font.getlength(text).
    """
    # This, of course, could be more efficient, but I'll worry
    # about that some other time (TODO)
    for font_name, font_file in list_fonts():
        if font_name.lower() == name.lower():
            return ImageFont.truetype(font_file, size)
    raise ValueError(f"font name '{name}' not found")

def main():
    #for name, filename in list_fonts():
    #    print(name, filename)

    sample_text = "Sample Text"
    print(f"Estimated width of '{sample_text}' at 10pt:")

    for font_name, _ in list_fonts():
        print(font_name, end=' ')
        font = get_font(font_name, 10)
        print(font.getlength(sample_text))

if __name__ == '__main__':
    main()







