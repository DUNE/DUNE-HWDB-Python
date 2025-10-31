#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/__init__.py
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

import os

#version = 'v1.3.0.rel.2025.07.21a'
version = 'v1.4.1.rel.2025.10.30b'

project_root = os.path.realpath(os.path.join(os.path.dirname(__file__), "../.."))

def get_path(path):
    """Get a path relative to the project root"""
    return os.path.realpath(os.path.join(project_root, path))

def display_header():
    import Sisyphus.Configuration as Config
    from Sisyphus.Utils.Terminal import Image
    from Sisyphus.Utils.Terminal.Style import Style
    import Sisyphus.Utils.Terminal.BoxDraw as box
    
    #columns = 66 # I forgot why I chose 66. Maybe the image lines up better?
    columns = 79
    padding = 4
    #bgcolor = 0x111111
    bgcolor = 0x000000

    filepath = get_path("resources/images/DUNE-short.png")
    img_text = Image.image2text(filepath, columns=columns-2*padding, background=bgcolor).split("\n")
    padding = Style.bg(bgcolor)(" "*padding)
    joiner = padding + "\n" + padding

    print(padding, end="")
    print(joiner.join(img_text), end="")
    print(padding)
    Style.notice.bold().print(f"DUNE HWDB Utility {version}".center(columns))

    if Config.config.newer_version_exists():
        url = "https://github.com/DUNE/DUNE-HWDB-Python/releases/latest"
        latest_version = Config.config.get_latest_release_version()
        print()

        message = (
            Style.notice(f"Notice: a newer version of this software ({latest_version}) is available.\n")
            + Style.notice("To download this version, go to:\n")
            + Style.link(url))

        print(box.MessageBox(message, width=columns-2, halign=box.HALIGN_CENTER))
    print()
