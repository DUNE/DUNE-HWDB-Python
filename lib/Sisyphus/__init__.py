#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/__init__.py
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from pathlib import Path
import os, sys

#version = 'v1.3.0.rel.2025.07.21a'
version = 'v1.7.5.rel.2026.03.13b'


project_root = os.path.realpath(os.path.join(os.path.dirname(__file__), "../.."))

def _runtime_root() -> Path:
    # Frozen (PyInstaller): _MEIPASS points to the extracted runtime dir.
    # In onedir builds, that means ".../dist/HWDBTools/_internal"
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent / "_internal"))

    # Non-frozen: keep our existing behavior
    if "project_root" in globals():
        return Path(project_root)

    # Fallback: walk upward from this file until we find a repo marker!
    here = Path(__file__).resolve()
    for p in [here] + list(here.parents):
        if (p / "lib").is_dir() and (p / "resources").is_dir():
            return p
    return here.parent


_RUNTIME_ROOT = _runtime_root()


def get_path(rel: str) -> str:
    rel = rel.lstrip("/").replace("\\", "/")
    return str(_RUNTIME_ROOT / rel)

#def get_path(path):
#    """Get a path relative to the project root"""
#    return os.path.realpath(os.path.join(project_root, path))




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
