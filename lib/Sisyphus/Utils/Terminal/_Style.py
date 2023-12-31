#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/Utils/Terminal/_Text.py
Copyright (c) 2022 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""
class Style:
    
    def __init__(self, *args, **kwargs):
        
        properties = ["fg", "bg", "ul", "bold", "faint", "italic", "blink", "inverse", "strike"]
        
        for propname in properties:
            setattr(self, propname, None)
        
        for arg in args:
            for propname in properties:
                if getattr(arg, propname, None) is not None:
                    setattr(self, propname, getattr(arg, propname))
        
        for propname in properties:
            if propname in ("fg", "bg") and propname in kwargs.keys():
                arg = kwargs[propname]
                if type(arg) is str:
                    if arg.lower() in Style.Colors.keys():
                        value = Style.Colors[arg.lower()]
                    elif arg.startswith("#"):
                        if len(arg) == 4:
                            value = tuple(17*int(arg[x:x+1],16) for x in (1, 2, 3))
                        elif len(arg) == 7:
                            value = tuple(int(arg[x:x+2],16) for x in (1, 3, 5))
                    else:
                        value = (0, 0, 0)
                elif type(arg) is int:
                    value = ( (arg & 0xff0000)>>16, (arg & 0xff00)>>8, arg & 0xff)
                elif type(arg) is tuple:
                    value = arg 
                else:
                    value = (0, 0, 0)
                    
                setattr(self, propname, value)
            else:    
                setattr(self, propname, kwargs.get(propname, getattr(self, propname, None)))
        
    @classmethod
    def fg(cls, color):
        return Style(fg=color)
    
    @classmethod
    def bg(cls, color):
        return Style(bg=color)
    
    Colors = \
    {
        "aliceblue":            (240, 248, 255),    "antiquewhite":         (250, 235, 215),
        "aqua":                 (  0, 255, 255),    "aquamarine":           (127, 255, 212),
        "azure":                (240, 255, 255),    "beige":                (245, 245, 220),
        "bisque":               ( 55, 228, 196),    "black":                (  0,   0,   0),
        "blanchedalmond":       (255, 235, 205),    "blue":                 (  0,   0, 255),
        "blueviolet":           (138,  43, 226),    "brown":                (165,  42,  42),
        "burlywood":            (222, 184, 135),    "cadetblue":            ( 95, 158, 160),
        "chartreuse":           (127, 255,   0),    "chocolate":            (210, 105,  30),
        "coral":                (255, 127,  80),    "cornflowerblue":       (100, 149, 237),
        "cornsilk":             (255, 248, 220),    "crimson":              (220,  20,  60),
                    
        "cyan":                 (  0, 255, 255),    "darkblue":             (  0,   0, 139),
        "darkcyan":             (  0, 139, 139),    "darkgoldenrod":        (184, 134,  11),
        "darkgray":             (169, 169, 169),    "darkgreen":            (  0, 100,   0),
        "darkgrey":             (169, 169, 169),    "darkkhaki":            (189, 183, 107),
        "darkmagenta":          (139,   0, 139),    "darkolivegreen":       ( 85, 107,  47),       
        "darkorange":           (255, 140,   0),    "darkorchid":           (153,  50, 204),
        "darkred":              (139,   0,   0),    "darksalmon":           (233, 150, 122),
        "darkseagreen":         (143, 188, 143),    "darkslateblue":        ( 72,  61, 139),
        "darkslategray":        ( 47,  79,  79),    "darkslategrey":        ( 47,  79,  79),
        "darkturquoise":        (  0, 206, 209),    "darkviolet":           (148,   0, 211),
        
        "deeppink":             (255,  20, 147),    "deepskyblue":          (  0, 191, 255),
        "dimgray":              (105, 105, 105),    "dimgrey":              (105, 105, 105),
        "dodgerblue":           ( 30, 144, 255),    "firebrick":            (178,  34,  34),
        "floralwhite":          (255, 250, 240),    "forestgreen":          ( 34, 139,  34),
        "fuchsia":              (255,   0, 255),    "gainsboro":            (220, 220, 220),
        "ghostwhite":           (248, 248, 255),    "gold":                 (255, 215,   0),
        "goldenrod":            (218, 165,  32),    "gray":                 (128, 128, 128),
        "green":                (  0, 128,   0),    "greenyellow":          (173, 255,  47),
        "grey":                 (128, 128, 128),    "honeydew":             (240, 255, 240),
        "hotpink":              (255, 105, 180),    "indianred":            (205,  92,  92),
        
        "indigo":               ( 75,   0, 130),    "ivory":                (255, 255, 240),
        "khaki":                (240, 230, 140),    "lavender":             (230, 230, 250),
        "lavenderblush":        (255, 240, 245),    "lawngreen":            (124, 252,   0),
        "lemonchiffon":         (255, 250, 205),    "lightblue":            (173, 216, 230),
        "lightcoral":           (240, 128, 128),    "lightcyan":            (224, 255, 255),
        "lightgoldenrodyellow": (250, 250, 210),    "lightgray":            (211, 211, 211),
        "lightgreen":           (144, 238, 144),    "lightgrey":            (211, 211, 211),
        "lightpink":            (255, 182, 193),    "lightsalmon":          (255, 160, 122),
        "lightseagreen":        ( 32, 178, 170),    "lightskyblue":         (135, 206, 250),
        "lightslategray":       (119, 136, 153),    "lightslategrey":       (119, 136, 153),
        
        "lightsteelblue":       (176, 196, 222),    "lightyellow":          (255, 255, 224),
        "lime":                 (  0, 255,   0),    "limegreen":            ( 50, 205,  50),
        "linen":                (250, 240, 230),    "magenta":              (255,   0, 255),
        "maroon":               (128,   0,   0),    "mediumaquamarine":     (102, 205, 170),
        "mediumblue":           (  0,   0, 205),    "mediumorchid":         (186,  85, 211),
        "mediumpurple":         (147, 112, 219),    "mediumseagreen":       ( 60, 179, 113),
        "mediumslateblue":      (123, 104, 238),    "mediumspringgreen":    (  0, 250, 154),
        "mediumturquoise":      ( 72, 209, 204),    "mediumvioletred":      (199,  21, 133),
        "midnightblue":         ( 25,  25, 112),    "mintcream":            (245, 255, 250),
        "mistyrose":            (255, 228, 225),    "moccasin":             (255, 228, 181),
        
        "navajowhite":          (255, 222, 173),    "navy":                 (  0,   0, 128),
        "oldlace":              (253, 245, 230),    "olive":                (128, 128,   0),
        "olivedrab":            (107, 142,  35),    "orange":               (255, 165,   0),
        "orangered":            (255,  69,   0),    "orchid":               (218, 112, 214),
        "palegoldenrod":        (238, 232, 170),    "palegreen":            (152, 251, 152),
        "paleturquoise":        (175, 238, 238),    "palevioletred":        (219, 112, 147),
        "papayawhip":           (255, 239, 213),    "peachpuff":            (255, 218, 185),
        "peru":                 (205, 133,  63),    "pink":                 (255, 192, 203),
        "plum":                 (221, 160, 221),    "powderblue":           (176, 224, 230),
        "purple":               (128,   0, 128),    "red":                  (255,   0,   0),
        
        "rosybrown":            (188, 143, 143),    "royalblue":            ( 65, 105, 225),
        "saddlebrown":          (139,  69,  19),    "salmon":               (250, 128, 114),
        "sandybrown":           (244, 164,  96),    "seagreen":             ( 46, 139,  87),
        "seashell":             (255, 245, 238),    "sienna":               (160,  82,  45),
        "silver":               (192, 192, 192),    "skyblue":              (135, 206, 235),
        "slateblue":            (106,  90, 205),    "slategray":            (112, 128, 144),
        "slategrey":            (112, 128, 144),    "snow":                 (255, 250, 250),
        "springgreen":          (  0, 255, 127),    "steelblue":            ( 70, 130, 180),
        "tan":                  (210, 180, 140),    "teal":                 (  0, 128, 128),
        "thistle":              (216, 191, 216),    "tomato":               (255,  99,  71),
        
        "turquoise":            ( 64, 224, 208),    "violet":               (238, 130, 238),
        "wheat":                (245, 222, 179),    "white":                (255, 255, 255),
        "whitesmoke":           (245, 245, 245),    "yellow":               (255, 255,   0),
        "yellowgreen":          (154, 205,  50),
    }
    
    def __call__(self, text):
        opener = ""
        closer = ""
        
        if self.fg is not None:
            r,g,b = self.fg
            opener += f"38;2;{r};{g};{b};"
            closer = "39;" + closer
        if self.bg is not None:
            r,g,b = self.bg
            opener += f"48;2;{r};{g};{b};"
            closer = "49;" + closer
        if self.ul:
            opener += "4;"
            closer = "24;" + closer
        if self.bold:
            opener += "1;"
            closer = "22;" + closer
        if self.faint:
            opener += "2;"
            closer = "22;" + closer
        if self.italic:
            opener += "3;"
            closer = "23;" + closer
        
        if self.blink:
            opener += "5;"
            closer = "25;" + closer
        if self.strike:
            opener += "4;"
            closer = "24;" + closer
        if self.inverse:
            opener += "7;"
            closer = "27;" + closer
        
        if len(opener) > 0:
            opener = f"\033[{opener[:-1]}m"
            closer = f"\033[{closer[:-1]}m"
        
        return f"{opener}{text}{closer}"
Style.ul = Style(ul=True)
Style.bold = Style(bold=True)
Style.faint = Style(faint=True)
Style.blink = Style(blink=True)
Style.strike = Style(strike=True)
Style.inverse = Style(inverse=True)
Style.italic = Style(italic=True)

# Some globally useful styles scripts could use
Style.info = Style()
Style.notice = Style.fg("royalblue")
Style.warning = Style.fg("goldenrod")
Style.error = Style.fg("red")
Style.success = Style.fg("green")


def highlight(text, substring, *, match_case=False):

    sub_len = len(substring)

    if match_case:
        cap_text = text
        cap_sub = substring
    else:
        cap_text = text.upper()
        cap_sub = substring.upper()

    parts = []

    last_end = 0
    while True:
        match_start = cap_text.find(cap_sub, last_end)
        if match_start == -1:
            break
        parts.append(text[last_end:match_start])
        next_end = match_start + sub_len
        parts.append(Style.inverse(text[match_start:next_end]))
        last_end = next_end
    parts.append(text[last_end:]) 

    return "".join(parts)

Style.highlight = highlight

def main():
    
    #warn = Style(Style.fg("yellow"))
    warn = Style(Style.fg("yellow"), Style.bg("green"))
    
    
    print(warn("yellow"))
    print(Style.fg("red")("red"))
    print(Style.ul("underline"))
    print(Style.fg("#336699")("blue"))
    print(Style.bg("green")("green"))
    
    print(Style.blink("blink"))
    print(Style.bold("bold"))
    print(Style.faint("faint"))
    
    faintred = Style(Style.fg("red"), Style.faint)
    boldred = Style(Style.fg("red"), Style.bold)
    print(faintred("faintred"))
    print(boldred("boldred"))
    
    print(Style.strike("strike"))
    print(Style.inverse("inverse"))
    print(Style.italic("italic"))
    
    for colorname in Style.Colors.keys():
        print(Style.fg(colorname)(colorname))
    
    
if __name__ == "__main__":
    main()





























