#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from Sisyphus.Utils.Terminal.Style import Style
from collections import abc
import shutil


BORDER_NORMAL = "normal"
BORDER_STRONG = "strong"

STRONG_MEANS_DOUBLE = "double"
STRONG_MEANS_THICK = "thick"

VALIGN_TOP = "top"
VALIGN_MIDDLE = "middle"
VALIGN_BOTTOM = "bottom"
HALIGN_LEFT = "left"
HALIGN_CENTER = "center"
HALIGN_RIGHT = "right"

class Table:
    default_width = 10
    default_height = 1
  
    default_border_color = 0x777777
 
    def __init__(self, source=None, /, **kwargs):
        #{{{
        
        source = kwargs.pop("source", source)
         
        if source is not None:
            self.set_source(source, **kwargs)

        else:
            self._columns = kwargs.get("columns", 1)
            self._rows = kwargs.get("rows", 1)
            self._resize()

        self._linestyle = kwargs.pop("linestyle", STRONG_MEANS_DOUBLE)
        self._auto_height = kwargs.pop("auto_height", True)
        self.border_color = kwargs.pop("border_color", self.default_border_color)
        #}}}

    # -----------------------------------------------------------------   

    # -----------------------------------------------------------------   

    def set_source(self, source, **kwargs):
        #{{{
        self._source = source
        self._rows = len(source)
        self._columns = len(source[0])
        self._resize()
        self.set_outer_border(kwargs.pop("outer_border", BORDER_STRONG))
        if self._rows > 0:
            self.set_row_border(1, kwargs.pop("first_row_border", BORDER_NORMAL))
        self.set_halign(kwargs.pop("halign", HALIGN_LEFT))
        self.set_valign(kwargs.pop("valign", VALIGN_TOP))

        # analyze the source to guess at good column widths and (tbd) heights
        
        for col_index in range(self._columns):
            max_width = 3
            for row_index in range(self._rows):
                cell_width = get_image_size(str(source[row_index][col_index]))
                max_width = max(max_width, cell_width)
            self.set_column_width(col_index, min(100, max_width))

        for row_index in range(self._rows):
            max_height = 1
            for col_index in range(self._columns):
                max_height = max(max_height, 1 + str(source[row_index][col_index]).count('\n'))
            self.set_row_height(row_index, max_height)
        #}}}

    # -----------------------------------------------------------------   

    def set_linestyle(self, linestyle):
        self._linestyle = linestyle

    # -----------------------------------------------------------------        

    def set_halign(self, halign, row=None, column=None):
        #{{{ 
        if row is None:
            row_iter = range(self._rows)
        else:
            if isinstance(row, abc.Sequence):
                row_iter = row 
            else:
                row_iter = [row]
            
        if column is None:
            col_iter = range(self._columns)
        else:
            if isinstance(column, abc.Sequence):
                col_iter = column
            else:
                col_iter = [column]
            
        for row_index in row_iter:
            for col_index in col_iter:
                self._halign[row_index][col_index] = halign
        #}}}    

    def set_valign(self, valign, row=None, column=None):
        #{{{
        if row is None:
            row_iter = range(self._rows)
        else:
            if isinstance(row, abc.Sequence):
                row_iter = row 
            else:
                row_iter = [row]
            
        if column is None:
            col_iter = range(self._columns)
        else:
            if isinstance(column, abc.Sequence):
                col_iter = column
            else:
                col_iter = [column]
            
        for row_index in row_iter:
            for col_index in col_iter:
                #print(row_index, col_index)
                self._valign[row_index][col_index] = valign
        #}}}

    # -----------------------------------------------------------------        

    @property
    def columns(self):
        return self._columns
    
    @columns.setter
    def columns(self, value):
        self._columns = value
        self._resize()

    # -----------------------------------------------------------------        

    @property
    def rows(self):
        return self._rows
    
    @rows.setter 
    def rows(self, value):
        self._rows = value
        self._resize()

    # -----------------------------------------------------------------        

    def set_column_width(self, col_index, width):
        self._column_widths[col_index] = width
        
    def get_column_width(self, col_index):
        return self._column_widths[col_index]

    # -----------------------------------------------------------------

    def set_row_height(self, row_index, height):
        self._row_heights[row_index] = height
        
    def get_row_width(self, row_index):
        return self._row_heights[row_index]

    # -----------------------------------------------------------------

    def set_row_border(self, row_index, border_style):
        self._row_borders[row_index] = border_style

    def set_column_border(self, column_index, border_style):
        self._column_borders[column_index] = border_style

    # -----------------------------------------------------------------

    def _resize(self):
        #{{{
        if getattr(self, "_column_borders", None) is None:
            setattr(self, "_column_borders", [])
        if getattr(self, "_row_borders", None) is None:
            setattr(self, "_row_borders", [])
        if getattr(self, "_row_heights", None) is None:
            setattr(self, "_row_heights", [])
            setattr(self, "_row_justify", [])
        if getattr(self, "_column_widths", None) is None:
            setattr(self, "_column_widths", [])
            setattr(self, "_column_justify", [])
            
        if getattr(self, "valign", None) is None:
            setattr(self, "_valign", [])
        if getattr(self, "halign", None) is None:
            setattr(self, "_halign", [])
            
        # add/trim _column_widths array until it's the right size
        while len(self._column_widths) < self._columns:
            self._column_widths.append(Table.default_width)
        while len(self._column_widths) > self._columns:
            self._column_widths.pop(-1)

        # add/trim _row_heights array until it's the right size
        while len(self._row_heights) < self._rows:
            self._row_heights.append(Table.default_height)
        while len(self._row_justify) < self._rows:
            self._row_justify.append(HALIGN_LEFT)
        while len(self._row_heights) > self._rows:
            self._row_heights.pop(-1)
        while len(self._row_justify) > self._rows:
            self._row_justify.pop(-1)

        # add/trim _column_borders array until it's the right size
        # (It should be one larger than the actual number of columns)
        while len(self._column_borders) < self._columns+1:
            self._column_borders.append(BORDER_NORMAL)
        while len(self._column_borders) > self._columns+1:
            self._column_borders.pop(-1)
        while len(self._column_justify) < self._columns+1:
            self._column_justify.append(VALIGN_TOP)
        while len(self._column_justify) > self._columns+1:
            self._column_justify.pop(-1)

        # add/trim _row_borders array until it's the right size
        # (It should be one larger than the actual number of rows)
        while len(self._row_borders) < self._rows+1:
            self._row_borders.append(BORDER_NORMAL)
        while len(self._row_borders) > self._rows+1:
            self._row_borders.pop(-1)
            
        # add/trim _halign
        while len(self._halign) < self._rows:
            self._halign.append([])
        while len(self._halign) > self._rows:
            self._halign.pop(-1)
        for halign_row in self._halign:
            while len(halign_row) < self._columns:
                halign_row.append(HALIGN_LEFT)
            while len(halign_row) > self._columns:
                halign_row.pop(-1)
            
        # add/trim _valign
        while len(self._valign) < self._rows:
            self._valign.append([])
        while len(self._valign) > self._rows:
            self._valign.pop(-1)
        for valign_row in self._valign:
            while len(valign_row) < self._columns:
                valign_row.append(HALIGN_LEFT)
            while len(valign_row) > self._columns:
                valign_row.pop(-1)
        #}}}

    def set_outer_border(self, style):
        #{{{
        self._row_borders[0] = style
        self._row_borders[self._rows] = style
        self._column_borders[0] = style
        self._column_borders[self._columns] = style
        #}}}

    def print(self, **kwargs):
        print(self.generate(), **kwargs)
    
    def generate(self, trunc_char=None, trunc_style=None):
        #{{{ 
        if self._linestyle == STRONG_MEANS_DOUBLE:
            STYLE = [
                [[('┌', '╓'), ('╒', '╔')],[('┬', '╥'), ('╤', '╦')],[('┐', '╖'), ('╕', '╗')],],

                [[('├', '╟'), ('╞', '╠')],[('┼', '╫'), ('╪', '╬')],[('┤', '╢'), ('╡', '╣')],],

                [[('└', '╙'), ('╘', '╚')],[('┴', '╨'), ('╧', '╩')],[('┘', '╜'), ('╛', '╝')],],
            ]
            HORIZ, VERT = ["─","═"], ["│","║"]
        else:
            STYLE = [
                [[('┌', '┎'), ('┍', '┏')],[('┬', '┰'), ('┯', '┳')],[('┐', '┒'), ('┑', '┓')],],

                [[('├', '┠'), ('┝', '┣')],[('┼', '╂'), ('┿', '╋')],[('┤', '┨'), ('┥', '┫')],],

                [[('└', '┖'), ('┕', '┗')],[('┴', '┸'), ('┷', '┻')],[('┘', '┚'), ('┙', '┛')],],
            ]
            HORIZ, VERT = ["─","━"], ["│","┃"]
 
        output = []       
        
        for row_index in range(self._rows+1):
            
            
            # take the current row and convert each cell to a sequence
            # of lines, so that we can more easily process multi-line
            # cells
            
            if row_index < self._rows:
                row_height = self._row_heights[row_index]
                
                # current_row_unjustified = \
                #     [
                #         cell.split("\n")
                #                 for cell in self._source[row_index]
                #     ]
                
                cells = self._source[row_index]
                current_row = []
                
                for col_index, cell in enumerate(cells):
                    col_width = self._column_widths[col_index]
                    halign = self._halign[row_index][col_index]
                    justified = fit_image_to_width(
                            cell, 
                            col_width, 
                            halign,
                            trunc_char, trunc_style).split('\n')
                    
                    if self._auto_height:
                        row_height = max(row_height, len(justified))
                    
                    current_row.append(justified)


                
                # we have all the cells in the row split into lines, but they
                # may be of all different number of lines, so let's walk through
                # and even them out, padding or trimming if necessary
           
                #old_current_row = current_row
                resized_row = []
                for col_index, cell in enumerate(current_row):
                    col_width = self._column_widths[col_index]
                    if len(cell) > row_height:
                        resized_row.append(cell[:row_height])
                    elif len(cell) < row_height:
                        vpadding = [' '*col_width] * (row_height-len(cell))
                        #print(row_index, col_index, self._valign)
                        valign = self._valign[row_index][col_index]
                        padded_cell = [] #LOLOLOL! Padded Cell??
                        if valign == HALIGN_CENTER:
                            top_pad = vpadding[:len(vpadding)//2]
                            bottom_pad = vpadding[len(vpadding)//2:]
                            padded_cell = [*top_pad, *cell, *bottom_pad]
                        elif valign == VALIGN_BOTTOM:
                            padded_cell = [*vpadding, *cell]
                        else: # assume VALIGN_TOP
                            padded_cell = [*cell, *vpadding]
                        resized_row.append(padded_cell)
                    else:
                        resized_row.append(cell)
                current_row = resized_row
           
            else:
                current_row = []  
                
            # Draw the edge above a row of cells, followed by the content of the row
            
            # Note that row_index may be past the actual number of rows, indicating that
            # we just need the bottom edge and no cell content row after
            
            # Handle border
            # -----------------
            if row_index == 0:
                row_position_index = 0
            elif row_index < self._rows:
                row_position_index = 1
            else:
                row_position_index = 2
                
            border_line = []            
            if row_index < self._rows:
                content_lines = [[] for i in range(self._row_heights[row_index])]
            
            for col_index in range(self._columns+1):
                if col_index == 0:
                    col_position_index = 0
                elif col_index < self._columns:
                    col_position_index = 1
                else:
                    col_position_index = 2
            
                # assemble border
                # ---------------
                if self._row_borders[row_index] == BORDER_STRONG:
                    row_border_emph_index = 1
                else:
                    row_border_emph_index = 0

                if self._column_borders[col_index] == BORDER_STRONG:
                    col_border_emph_index = 1
                else:
                    col_border_emph_index = 0

                ch = (STYLE[row_position_index][col_position_index]
                        [row_border_emph_index][col_border_emph_index])
                
                border_line.append(ch)
                
                if col_index < self._columns:
                    ch = HORIZ[row_border_emph_index] * self._column_widths[col_index]
                    border_line.append(ch)
            
                # assemble cell contents
                # ----------------------
                if row_index < self._rows:
                    
                    for line_no in range(self._row_heights[row_index]):
                    
                        ch = VERT[col_border_emph_index]
                        content_lines[line_no].append(Style.fg(self.border_color)(ch))
                        
                        if col_index < self._columns:
                            if self._source is not None:
                                # print("current_row_unjustified", current_row_unjustified)
                                # print("old_current_row", old_current_row)
                                # print("current_row:", current_row)
                                # print("col_index:", col_index)
                                # print("line_no", line_no)
                                ch = current_row[col_index][line_no]
                            else:
                                if line_no == 0:
                                    ch = f"{row_index},{col_index}"
                                else:
                                    ch = ""
                                
                            # width = self._column_widths[col_index]
                            # if self._halign[row_index][col_index] == HALIGN_LEFT:
                            #     ch = ch.ljust(width)
                            # elif self._halign[row_index][col_index] == HALIGN_RIGHT:
                            #     ch = ch.rjust(width)
                            # else:
                            #     ch = ch.center(width)
                                
                            # if len(ch) > width:
                            #     ch = ch[:width-3] + "..."
                                
                            content_lines[line_no].append(ch)
            
            #border_line.append("\n")
            #stdout.write(str.join("", border_line))
            output.append(Style.fg(self.border_color)(str.join("", border_line)))
            
            
            if row_index < self._rows:
                for line in content_lines:
                    #line.append("\n")
                    #stdout.write(str.join("", line))
                    output.append(str.join("", line))

        return str.join("\n", output)
        #}}}






def MessageBox(message, /, **kwargs):
    #{{{
    default_width = shutil.get_terminal_size().columns
    
    if kwargs.pop("pad_vertical", False):
        message = str.join("\n", 
                ["", kwargs.pop("message", message), ""])
    else:
        message = kwargs.pop("message", message)
        
    box = Table([[message]])
    box.set_outer_border(kwargs.pop("outer_border", BORDER_NORMAL))
    box.border_color = kwargs.pop("border_color", box.default_border_color)
    box.set_column_width(0, kwargs.pop("width", default_width-2))
    box.set_row_height(0, message.count('\n') + 1)
    box.set_halign(kwargs.pop("halign", HALIGN_LEFT))
    box.set_valign(kwargs.pop("valign", VALIGN_TOP))
    
    return box.generate()
    #}}}

def fit_image_to_width(img_str, width, halign=HALIGN_LEFT, trunc_char=None, trunc_style=None):
    i, w = _image_dimension_workhorse(img_str, width, halign, trunc_char, trunc_style)
    return i

def get_image_size(img_str):
    i, w = _image_dimension_workhorse(img_str, None, None)
    return w
    
def _image_dimension_workhorse(img_str, trim_to_width=None, halign=None, trunc_char=None, trunc_style=None):
 
    lines = str(img_str).split('\n')
    fixed_lines = []
    image_width = 0
    
    trunc_char = trunc_char or ''
    trunc_char_len = len(trunc_char)
    if trunc_style:
        trunc_char = trunc_style(trunc_char)

    for line in lines:
        char_count, width_count = 0, 0
        in_esc = False
        in_bracket = False
        esc_has_been_used = False

        add_trunc_char = False        

        for ch in line:
            
            #if trim_to_width is not None and width_count == trim_to_width:
            #    break
            
            if trim_to_width:
                # when the width reaches the point where the trunc_char would
                # be displayed, remember where we are now, but wait until we
                # actually exceed trim_to_width to break out, because if we
                # don't, we don't want to display the trunc_char, either.
                if width_count == trim_to_width - trunc_char_len:
                    state = char_count, width_count, in_esc, in_bracket, esc_has_been_used
                    #print(f"save state: {state}")
                elif width_count == trim_to_width:
                    char_count, width_count, in_esc, in_bracket, esc_has_been_used = state
                    #print(f"restore state: {state}")
                    add_trunc_char = True
                    break


            char_count += 1
            
            if not in_esc:
                if ch == "\033":
                    in_esc = True
                    continue
                else:
                    width_count += 1
                    continue
            elif not in_bracket:
                if ch == "[":
                    in_bracket = True
                    esc_has_been_used = True
                    continue
                else:
                    # esc was not followed by bracket, so forget it
                    in_esc = False
                    width_count +=2
                    continue
            elif ch == 'm':
                # escape sequence ends
                in_esc = False
                in_bracket = False
                continue
            else:
                # inside escape sequence
                continue
       
        if add_trunc_char:
            newline = [line[:char_count] + trunc_char]
            width_count += trunc_char_len
        else:        
            newline = [line[:char_count]]

        if esc_has_been_used:
            newline.append('\033[m')
        if trim_to_width is not None and width_count < trim_to_width:
            padding = ' ' * (trim_to_width-width_count)
            if halign == HALIGN_CENTER:
                left_padding, right_padding = [padding[:len(padding)//2], padding[len(padding)//2:]]
                newline.insert(0, left_padding)
                newline.append(right_padding)
            elif halign == HALIGN_RIGHT:
                newline.insert(0, padding)
            else: # assume halign==HALIGN_LEFT
                newline.append(padding)
        else:
            image_width = max(image_width, width_count)
            
        fixed_lines.append(str.join('', newline))
    if trim_to_width is not None:
        image_width = trim_to_width
    trimmed_image = str.join('\n', fixed_lines)
    return trimmed_image, image_width

def run_tests():

    def char_table():
        start = 0x2500
        #start = 0x1fb0
        table = [ 
            [
                "", 
                *[hex(x) for x in range(16)]
            ], 
            *[  
                [
                    hex(start+x*16), 
                    *[ chr(start+x*16+y) for y in range(16)]
                ] for x in range(12) 
            ] 
        ]
        
        box = Table(table, halign=HALIGN_CENTER)
        box.set_linestyle(STRONG_MEANS_THICK)
        
        #print(box.rows, box.columns)
        
        for c in range(len(table[0])):
            box._column_widths[c] = 3
            #box._column_justify[c] = HALIGN_CENTER
        for r in range(len(table)):
            box._row_heights[r] = 1
   
        box._column_widths[0]=10
        box.set_outer_border(BORDER_STRONG)    
        box._row_borders[1] = BORDER_STRONG
        box._column_borders[1] = BORDER_STRONG
     
        box.display()

    def csv_table():
        from Sisyphus.Config import config
        import os.path
        import csv
        
        test_filename = os.path.join(config["project_root"], "lib/Sisyphus/test/data/sample1.csv")
        
        with open(test_filename) as csvfile:
            rdr = csv.reader(csvfile) #, delimiter=' ', quotechar='|')
            
            table = [row for row in rdr]
            
        box = Table(source=table)
        box.set_halign(HALIGN_RIGHT)
        
        box.display()

    def ods_table():
        from Sisyphus.Config import config
        import os.path
        import pandas as pd
        
        test_filename = os.path.join(config["project_root"], "lib/Sisyphus/test/data/sample1.ods")

        ods_table = pd.read_excel(test_filename)
        
        table = [ 
                    list(ods_table.columns),
                    *[[str(c) for c in row] for row in ods_table.to_numpy()]
                ]

        box = Table(source=table)
        box.set_halign(HALIGN_RIGHT)
        
        box.display()



    def image_table():
        from Sisyphus.Config import config
        import os.path
        
        img_dir = os.path.join(config["project_root"], "img")
        
        img_files = os.listdir(img_dir)
        
        table = [['Filename', 'Image Preview']]
        
        for filename in img_files:
            full_filename = os.path.join(img_dir, filename)
            try:
                image_str = preview_image(full_filename, max_width=60)
            except Exception:
                image_str = "Not an image"
            table.append([filename, image_str])
        
        box = Table(source=table)
        #box.set_column_width(1, 30)
        box.display()
        
    print(Table.Message("Testing:\nbox drawing character table"))
    print()
    char_table()
    print()
    
    # print(Table.Message("Testing:\nload table from csv file"))
    # print()
    # csv_table()
    # print()

    print(Table.Message("Testing:\ntable containing images"))
    print()
    image_table()
    print()

    #print(Table.Message("Testing:\nload table from ods file"))
    #print()
    #ods_table()
    #print()





if __name__ == "__main__":
    run_tests()


