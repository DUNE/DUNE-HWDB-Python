#!/usr/bin/env python

#from Sisyphus.Configuration import config
#logger = config.getLogger(__name__)

import sys

from Sisyphus.Utils.Terminal.Style import Style


def main(argv):
    print( Style(fg="red")("This should be red."))
    print( Style(fg="black", bg="red")("This should be black on red"))

    teststyle = Style.fg("cornflowerblue").bg("blanchedalmond").italic()

    teststyle.print("abc", 123)
    print(teststyle("abc 123"))


if __name__ == '__main__':
    sys.exit(main(sys.argv))
