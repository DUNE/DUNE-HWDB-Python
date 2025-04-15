#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Author: Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
"""

from collections import abc
import shutil

class ProgressBar:
    def __init__(self, total, prefix='', suffix='', decimals=1, length=100, 
                    fill='█', printEnd='\r'):
        self.iteration = 0
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = decimals
        self.length = length
        self.fill = fill
        self.printEnd = printEnd
        self.update(self.iteration)
        
    def update(self, iteration):
        self.iteration = iteration
        percent = ("{0:." + str(self.decimals) + "f}").format(
                        100 * (self.iteration / float(self.total))).rjust(5)
        #print(length, type(length), iteration, type(iteration), total, type(total))
        filledLength = int(self.length * self.iteration // self.total)
        bar = self.fill * filledLength + '-' * (self.length - filledLength)
        print(f'\r{self.prefix} |{bar}| {percent}% {self.suffix}', end = self.printEnd)
        # Print New Line on Complete
        if self.iteration == self.total: 
            print()

def run_tests():
    pass

if __name__ == "__main__":
    run_tests()


