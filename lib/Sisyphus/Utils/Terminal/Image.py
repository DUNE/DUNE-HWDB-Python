#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

import PIL.Image
import shutil
import io


def image2text(source, 
            columns=None, lines=None,
            max_columns=None, max_lines=None,
            background=None):
    #{{{
    
    # PIL.Image.open() will recognize if source is a filename that it needs
    # to open or if it's already a file pointer, but it won't know what to
    # do with raw bytes, so for convenience, we can make it act like a 
    # file pointer.
    if type(source) is bytes:
        source = io.BytesIO(source)

    full_image = PIL.Image.open(source) 
    
    if full_image.mode == 'P':
        full_image = full_image.convert("RGB")

    aspect_ratio = full_image.width / full_image.height * 2 
    
    if columns is not None:
        num_columns = columns
        if lines is not None:
            num_lines = lines
        else:
            num_lines = int(num_columns / aspect_ratio + 0.5)
    elif lines is not None:
        num_lines = lines
        num_columns = int(num_lines * aspect_ratio + 0.5)
    else:
        if max_columns is None:
            max_columns = shutil.get_terminal_size().columns
        
        num_columns = min(full_image.width, max_columns)

        # Calculate what we need to scale the size to.
        # Each cell has an upper and lower half, so each line has 2 rows. 

        # Start by calculating the width
        scale = full_image.width / num_columns
        num_lines = int(full_image.height / scale / 2)

        # If the resultant number of lines is too large, we need to redo
        # the calculations.
        if max_lines is not None and num_lines > max_lines:
            num_lines = max_lines
            scale = full_image.height / num_lines / 2
            num_columns = int(full_image.width / scale)

    if type(background) is int:
        background = (background & 0xff0000)>>16, (background & 0xff00)>>8, (background & 0xff)

    if background is not None:
        bg_parity_0 = (background, background)
        bg_parity_1 = (background, background)
    else:
        # This will make a checkerboard pattern
        bg_parity_0 = ((0, 0, 0), (64, 64, 64))
        bg_parity_1 = ((64, 64, 64), (0, 0, 0))
    
    image = full_image.resize((num_columns*2, num_lines*2))
    mode = image.mode
   
    output = []
 
    def resolve_alpha(rgba, color):
        # Take a color with an alpha channel and blend it with the
        # background according to that alpha.
        r, g, b, a = rgba
        rr, gg, bb = color
        A = a ^ 0xff
        c = tuple( (fore * a + back * A) // 0xff for fore, back in ((r, rr), (g, gg), (b, bb)) )
        return c

    def blend(*colors):
        return tuple(x//len(colors) for x in map(sum, zip(*colors)))

    def trial(group1, group2):
        blend1 = blend(*group1)
        blend2 = blend(*group2) if len(group2) > 0 else blend1
        err = sum(sum(sum( (comp - blend_comp)**2 for comp, blend_comp in zip(color, blend))
                for color in group) for group, blend in ((group1, blend1), (group2, blend2)))
        return err, blend1, blend2

    def best_fit(TL, TR, BL, BR):

        trials = (
            (*trial( (TL, TR, BL, BR), () ), chr(0x2588), chr(0x0020)),
            (*trial( (TL, TR), (BL, BR)   ), chr(0x2580), chr(0x2584)),
            (*trial( (TL, BL), (TR, BR)   ), chr(0x258c), chr(0x2590)),
            (*trial( (TL, BR), (TR, BL)   ), chr(0x259a), chr(0x259e)),
            (*trial( (TL,), (TR, BL, BR)  ), chr(0x2598), chr(0x259f)),
            (*trial( (TR,), (TL, BL, BR)  ), chr(0x259d), chr(0x2599)),
            (*trial( (BL,), (TL, TR, BR)  ), chr(0x2596), chr(0x259c)),
            (*trial( (BR,), (TL, TR, BL)  ), chr(0x2597), chr(0x259b)),
        )

        # insert an index so that we can preferentially return the item
        # with a lower index first if there's a tie.
        trials = [ (x[0], i, *x[1:]) for i, x in enumerate(trials) ]

        #print( "\n".join([str(trial) for trial in sorted(trials)]))
        #exit()

        return min(trials)[2:]

    use_alternate_block_types = False
    use_bw_text = True

    for line_index in range(0, num_lines):
        img_row = 2 * line_index
        line_content = []
        for column_index in range(num_columns):
            img_col = 2 * column_index            
            block_parity = (column_index + img_row) % 2

            TL = image.getpixel((img_col, img_row))
            TR = image.getpixel((img_col+1, img_row))
            BL = image.getpixel((img_col, img_row+1))
            BR = image.getpixel((img_col+1, img_row+1))

            if mode == 'RGBA':
                TL = resolve_alpha(TL, bg_parity_0[block_parity])
                TR = resolve_alpha(TR, bg_parity_0[block_parity])
                BL = resolve_alpha(BL, bg_parity_1[block_parity])
                BR = resolve_alpha(BR, bg_parity_1[block_parity])

            fore, back, char1, char2 = best_fit(TL, TR, BL, BR)

            if use_alternate_block_types:
                if block_parity:
                    fore, back, char = fore, back, char1
                else:
                    fore, back, char = back, fore, char2
            elif use_bw_text:
                if char2 == " ":
                    if sum(fore) > 128:
                        fore, back, char = fore, back, char1
                    else:
                        fore, back, char = back, fore, char2
                else:
                    if sum(fore) > sum(back):
                        fore, back, char = fore, back, char1
                    else:
                        fore, back, char = back, fore, char2
            else:
                #fore, back, char = fore, back, char1
                fore, back, char = back, fore, char2

 
            line_content.append(f"\033[48;2;{back[0]};{back[1]};{back[2]}"
                          f";38;2;{fore[0]};{fore[1]};{fore[2]}m{char}")

        line_content.append("\033[0m")
        output.append(str.join('', line_content))
    return str.join('\n', output)
    #}}}


def run_tests():
    import sys, os

    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = os.path.join(os.path.dirname(__file__), "DUNE-short.png")

    imagetext = image2text(filename, background=0x000000)
    print(imagetext)

if __name__ == "__main__":
    run_tests()

