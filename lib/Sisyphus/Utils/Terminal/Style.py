#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sisyphus/Utils/Terminal/_Style.py
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Utils.utils import objectmethod
from Sisyphus.Utils.Terminal import Colors


class Style:
    def __init__(self, *args, **kwargs):
        #{{{       
 
        # Property names and the private variables containing those properties
        properties = \
        {
            "fg": "_fg", 
            "bg": "_bg", 
            "underline": "_underline", 
            "underscore": "_underscore",
            "overline": "_overline",
            "bold": "_bold", 
            "faint": "_faint", 
            "italic": "_italic", 
            "blink": "_blink", 
            "inverse": "_inverse", 
            "strike": "_strike",
            "large": "_large",
            "wide": "_wide",
        }
        
        for propname, propvar in properties.items():
            setattr(self, propvar, None)
    
        # I think this was expecting "args" to contain style objects,
        # and this was trying to aggregate the properties of the styles
        # that were passed?    
        for arg in args:
            for propname, propvar in properties.items():
                if getattr(arg, propvar, None) is not None:
                    setattr(self, propvar, getattr(arg, propvar))
        
        # The kwargs spell out the desired properties for our new style
        for propname, propvar in properties.items():
            if propname in ("fg", "bg") and propname in kwargs.keys():
                arg = kwargs[propname]
                setattr(self, propvar, Colors.color(arg))
            else:    
                setattr(self, propvar, kwargs.get(propname, getattr(self, propvar, None)))
        #}}}
  
    def print(self, *args, **kwargs):
        opener, closer = self.get_codes()
        #args = [ opener, *args, closer ]
        #print(*args, **kwargs)
        print(opener, **{**kwargs, 'end':'', 'sep':''})
        print(*args, **{**kwargs, 'end':''})
        print(closer, **kwargs)

 
    #{{{     
    @objectmethod
    def fg(self, color):
        if self is type:
            return Style(fg=color)
        else:
            return Style(self, fg=color)
    
    @objectmethod
    def bg(self, color):
        if self is type:
            return Style(bg=color)
        else:
            return Style(self, bg=color)
    
    @objectmethod
    def underline(self, status=True):
        if self is type:
            return Style(underline=status)
        else:
            return Style(self, underline=status)
    
    @objectmethod
    def underscore(self, status=True):
        if self is type:
            return Style(underscore=status)
        else:
            return Style(self, underscore=status)
    
    @objectmethod
    def overline(self, status=True):
        if self is type:
            return Style(overline=status)
        else:
            return Style(self, overline=status)

    @objectmethod
    def bold(self, status=True):
        if self is type:
            return Style(bold=status)
        else:
            return Style(self, bold=status)
    
    @objectmethod
    def blink(self, status=True):
        if self is type:
            return Style(blink=status)
        else:
            return Style(self, blink=status)
    
    @objectmethod
    def faint(self, status=True):
        if self is type:
            return Style(faint=status)
        else:
            return Style(self, faint=status)
    @objectmethod
    def italic(self, status=True):
        if self is type:
            return Style(italic=status)
        else:
            return Style(self, italic=status)

    @objectmethod
    def strike(self, status=True):
        if self is type:
            return Style(strike=status)
        else:
            return Style(self, strike=status)

    @objectmethod
    def inverse(self, status=True):
        if self is type:
            return Style(inverse=status)
        else:
            return Style(self, inverse=status)
    
    @objectmethod
    def large(self, status=True):
        if self is type:
            return Style(large=status)
        else:
            return Style(self, large=status, wide=not status and self._wide)

    @objectmethod
    def wide(self, status=True):
        if self is type:
            return Style(wide=status)
        else:
            return Style(self, wide=status, large=not status and self._large)
    #}}}    

    def get_codes(self):
        #{{{
        opener = ""
        closer = ""
        
        if self._fg is not None:
            r,g,b = self._fg
            opener += f"38;2;{r};{g};{b};"
            closer = "39;" + closer
        if self._bg is not None:
            r,g,b = self._bg
            opener += f"48;2;{r};{g};{b};"
            closer = "49;" + closer
        if self._underline:
            opener += "4;"
            closer = "24;" + closer
        if self._underscore:
            opener += "21;"
            closer = "24;" + closer
        if self._overline:
            opener += "53;"
            closer = "55;" + closer
        if self._bold:
            opener += "1;"
            closer = "22;" + closer
        if self._faint:
            opener += "2;"
            closer = "22;" + closer
        if self._italic:
            opener += "3;"
            closer = "23;" + closer
        if self._blink:
            opener += "5;"
            closer = "25;" + closer
        if self._strike:
            opener += "9;"
            closer = "29;" + closer
        if self._inverse:
            opener += "7;"
            closer = "27;" + closer
        
        if len(opener) > 0:
            # the [:-1] part is to trim off the last semicolon.
            opener = f"\033[{opener[:-1]}m"
            closer = f"\033[{closer[:-1]}m"

        return opener, closer
        #}}}
    
    def __call__(self, text):
        #{{{

        opener, closer = self.get_codes()

        # These have to be handled separately becaunderscoree they are not
        # CSI (i.e. ESC[ ) codes ending with 'm'
        WIDE="\033#6"
        LARGETOP="\033#3"
        LARGEBOTTOM="\033#4"
        if self._wide:
            return f"\033#6{opener}{text}{closer}"
        elif self._large:
            lines = text.split("\n")
            trailing_newline = False
            if len(lines) > 1 and len(lines[-1])==0:
                lines.pop()
                trailing_newline = True
            result = []
            for line in lines:
                result.append(f"{LARGETOP}{line}")
                result.append(f"{LARGEBOTTOM}{line}")
            result = [opener, "\n".join(result), closer]
            if trailing_newline:
                result.append("\n")
            return "".join(result)
            #return  f"{opener}{LARGETOP}{text}\n{LARGEBOTTOM}{text}{closer}"
        else:
            return f"{opener}{text}{closer}"
        #}}}

#Style.ul = Style(ul=True)
#Style.bold = Style(bold=True)
#Style.faint = Style(faint=True)
#Style.blink = Style(blink=True)
#Style.strike = Style(strike=True)
#Style.inverse = Style(inverse=True)
#Style.italic = Style(italic=True)

# Some globally useful styles scripts could use
Style.debug = Style.fg(0x999999)
#Style.info = Style.fg(0x3b78ff).bold()
Style.info = Style.fg(0x628dff).bold()
Style.warning = Style.fg(0xffaa22)
Style.error = Style.fg(0xe74856).bold()
Style.critical = Style.fg(0xcccccc).bg(0xe74856)

Style.test = Style.fg(0xffffff).bg(0x881798).bold()
Style.success = Style.fg(0xffffff).bg(0x13a10e).bold()
Style.fail = Style.fg(0xffffff).bg(0xc50f1f).bold()

Style.notice = Style.fg(0xccaa00).italic()
Style.link = Style.fg(0x6699ff).bold().italic().underline()


Style.cursor_up = lambda n: f'\033[{n}A'
Style.cursor_down = lambda n: f'\033[{n}B'
Style.cursor_forward = lambda n: f'\033[{n}C'
Style.cursor_back = lambda n: f'\033[{n}D'
Style.cursor_move_vertical = lambda n: f'\033[{n}E' if n>=0 else f'\033[{-n}F'
Style.cursor_abs_horizontal = lambda n: f'\033[{n}G'
Style.cursor_position = lambda n, m: f'\033[{n};{m}H'
Style.cursor_store = '\033[s'
Style.cursor_recall = '\033[u'

Style.clear_to_bottom = '\033[0J'
Style.clear_to_top = '\033[1J'
Style.clear_screen = '\033[2J'
Style.clear_buffer = '\033[3J'
Style.erase_right = '\033[0K'
Style.erase_left = '\033[1K'
Style.erase_line = '\033[2K'
Style.scroll_up = lambda n: '\033[{n}S'
Style.scroll_down = lambda n: '\033[{n}T'



###############################################################################

def highlight(text, substring, *, match_case=False, style=Style.inverse()):
    #{{{
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
        parts.append(style(text[match_start:next_end]))
        last_end = next_end
    parts.append(text[last_end:]) 

    return "".join(parts)
    #}}}
#Style.highlight = highlight

###############################################################################

def fix_emoji_widths(s):
    """If a string contains emojis, fix the ones with bad widths

    I don't know about other terminals, but Windows Terminal messes up
    the widths of some emojis. Some are display 2-characters wide, while
    others are only 1-character wide. Insert an extra space in the 1-char
    emojis, so that it takes up 2 characters.
    """
    return "".join([ c if c not in BAD_WIDTH_CHARS else (c+" ") for c in s ]) 
Style.fix_emoji_widths = fix_emoji_widths

BAD_WIDTH_CHARS = [ 
    #{{{
    chr(c) for c in [
        # 0x1f000
        *[i for i in range(0x1f000, 0x1f100) if i not in (0x1f004, 0x1f0cf)],
        # 0x1f100
        *range(0x1f100, 0x1f18e), 0x1f18f, 0x1f191, *range(0x1f19b, 0x1f1e6),

        # 0x1f200
        *range(0x1f203, 0x1f210), *range(0x1f23c, 0x1f240), *range(0x1f249, 0x1f250),
        *range(0x1f252, 0x1f260), *range(0x1f266, 0x1f300),

        # 0x1f300
        *range(0x1f321, 0x1f32d), 0x1f336, 0x1f37d, *range(0x1f394, 0x1f3a0),
        *range(0x1f3cb, 0x1f3cf), *range(0x1f3d4, 0x1f3e0), *range(0x1f3f1, 0x1f3f4),
        *range(0x1f3f5, 0x1f3f8),

        # 0x1f400
        0x1f441, 0x1f43f, 0x1f4fd, 0x1f4fe,

        # 0x1f500
        *range(0x1f53e, 0x1f54b), 0x1f54f, *range(0x1f568, 0x1f57a),
        *range(0x1f57b, 0x1f595), *range(0x1f597, 0x1f5a4), *range(0x1f5a5, 0x1f5fb),

        # 0x1f600
        *range(0x1f650, 0x1f680), *range(0x1f6c6, 0x1f6cc), 0x1f6cd, 0x1f6ce, 0x1f6cf,
        0x1f6d3, 0x1f6d4, 0x1f6d8, 0x1f6d9, 0x1f6da, 0x1f6db, *range(0x1f6e0, 0x1f6eb),
        *range(0x1f6ed, 0x1f6f4), *range(0x1f6fd, 0x1f700),

        # 0x1f700
        *range(0x1f700, 0x1f7e0), *range(0x1f7ec, 0x1f7f0), *range(0x1f7f1, 0x1f800),

        # 0x1f800
        *range(0x1f800, 0x1f900),

        # 0x1f900
        *range(0x1f900, 0x1f90c), 0x1f93b, 0x1f946,

        # 0x1fa00
        *range(0x1fa00, 0x1fa70), *range(0x1fa7d, 0x1fa80), *range(0x1fa89, 0x1fa90),
        0x1fabe, *range(0x1fac6, 0x1face), *range(0x1fadc, 0x1fae0),
        *range(0x1fae9, 0x1faf0), *range(0x1faf9, 0x1fb00),

        # 0x1fb00 - 0x20000
        # Maybe let's not worry about the rest
        #*range(0x1fb00, 0x20000),
    ]
    #}}}
]

###############################################################################

def main():
    import textwrap

    #print("\033[1;2]\033[4mUnderline\033[0m")
    warn = Style.fg("yellow").bg("green")

    print(warn("yellow on green"))
    print()    
    print(Style.underline()("underline"))
    print()    
    print(Style.underscore()("underscore"))
    print()    
    print(Style.overline()("overline"))
    print()    
    print(Style.underscore().overline()("underscore-overline"))
    print()    
    print(Style.fg("#336699")("blue"))
    print()    
    print(Style.bg("green")("green"))
    print()    
    
    print(Style.blink(True)("blink"))
    print()    
    print(Style.bold(True)("bold"))
    print()    
    print(Style.faint(True)("faint"))
    print()    

    red = Style.fg("red")
    faintred = red.faint()
    boldred = red.bold()

    print(" ".join([ faintred("faintred"), red("red"), boldred("boldred") ]))
    print()
    print(Style.strike()("strike"))
    print()    
    print(Style.inverse()("inverse"))
    print()    
    print(Style.italic()("italic"))
    print()    
    print(Style.large()("Large"))   
    print()
    print(Style.wide()("Wide"))
    print()
    print(Style.highlight("ABCDE", "BCD", style=Style.fg("tomato").inverse()))
    print()
    multiple = Style.fg("cornflowerblue").underline().overline().large()
    print(multiple("\U0001f600 blue, underlined, overlined, large"))
    print()
 
    s = []
    for colorname in Style.Colors.keys():
        s.append(Style.fg(colorname)(colorname))
        #s.append(colorname)
    text = " ".join(s)
    #print(s)
    #print(text)
    print("\n".join(textwrap.wrap(text, width=300)))

    # note, this isn't all the emojis, but we'll know if the fix worked if
    # we try these
    start = 0x1f300
    end = 0x1f600

    bad_chars =  [chr(x) for x in 
    [
        *range(0xd800, 0xdc80),
        *range(0xdd00, 0xe000),
    ]]

    emojis = \
        [
            hex(x) + " " + " ".join([ chr(c) for c in range(x, x+16)]) 
            for x in range(start, end, 0x10) 
        ]
    for line in emojis:
        for badchar in bad_chars:
            line = line.replace(badchar, "[bad]")
        print(Style.large()(fix_emoji_widths(line)))


if __name__ == "__main__":
    main()

'''

some useful console codes that maybe I'll use in the future:


ESC [ ? 5 h
ESC [ ? 5 l

    Set/Reset reverse video mode ... might be useful to "flash" the screen

ESC ] 0 ; <text> BEL

    Sets the title of the terminal. BEL probably \a or \007

ESC [ n A       Cursor up
ESC [ n B       Cursor down
ESC [ n C       Cursor forward
ESC [ n D       Cursor back
ESC [ n E       Cursor next line
ESC [ n F       Cursor previous line
ESC [ n G       Cursor horizontal absolute
ESC [ n ; m H   Cursor position
ESC [ 0 J       Clear from cursor to end of screen (0 may be omitted)
ESC [ 1 J       Clear from cursor to beginning of screen
ESC [ 2 J       Clear the screen (but not the entire buffer)
ESC [ 3 J       Clear the screen and the buffer
ESC [ 0 K       Erase to end of line (0 may be omitted)
ESC [ 1 K       Erase to beginning of line
ESC [ 2 K       Erase entire line
ESC [ n S       Scroll up
ESC [ n T       Scroll down

ESC [ 6n        Report the cursor position 

ESC # 3         Double-size characters on this line, top half
ESC # 4         Double-size characters on this line, bottom half
ESC # 5         normal-size characters on this line
ESC # 6         Double-wide characters on this line (discard 2nd half of line)

ESC ]11;rgb:xx/yy/zz ESC \\   change background color


ESC [? 25 h      Show cursor
ESC [? 25 l      Hide cursor
ESC [? 1049 h    Enable alternative screen buffer
ESC [? 1049 l    Disable alternative screen buffer

ESC [s          Save cursor position
ESC 7           Save cursor position (DEC)

ESC [u          Restore cursor position
ESC 8           Restore cursor position (DEC)

ESC [ n L       Insert n lines
ESC [ n M       Delete n lines
ESC [ n P       Delete n chars




https://invisible-island.net/xterm/ctlseqs/ctlseqs.html











'''
