#!/usr/bin/env python

#from Sisyphus.Configuration import config
#logger = config.getLogger(__name__)

import sys

import Sisyphus
from Sisyphus.Utils.Terminal import BoxDraw
from Sisyphus.Utils.Terminal import Image




def main(argv):

    image = Image.image2text(Sisyphus.get_path("scratch/images/apple.jpeg"), max_columns=20)
    contents = \
    [
        ['aaaaaaaaaa', 'bbbbbbbbbb', 'cccccccccc', 'dddddddddd'], 
        ['ddd', 'eee', 'fff', 'ggg'], 
        ['ggg', 'hhh', image, 'iii']
    ]

    table = BoxDraw.Table(contents)

    table.set_halign(BoxDraw.HALIGN_CENTER, row=1, column=1)
    table.set_linestyle(BoxDraw.STRONG_MEANS_THICK)


    table.print()

    print(BoxDraw.MessageBox(
                "Hello!", 
                halign=BoxDraw.HALIGN_CENTER, 
                pad_vertical=True,
                width=50))



if __name__ == '__main__':
    sys.exit(main(sys.argv))
