#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Authors: 
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
    Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy

Test RestApiV1 functions related to getting images
"""

from Sisyphus.Configuration import config
logger = config.getLogger(__name__)
from Sisyphus.Utils import UnitTest as unittest

import os, shutil
import json
import unittest
import random
import matplotlib as mpl
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from datetime import datetime
import time

from Sisyphus.RestApiV1 import get_hwitem
#from Sisyphus.RestApiV1 import get_hwitem_image_list
#from Sisyphus.RestApiV1 import get_component_type_image_list
from Sisyphus.RestApiV1 import get_image
from Sisyphus.RestApiV1 import post_hwitem_image
from Sisyphus import RestApiV1 as ra
from Sisyphus.Utils.Terminal.Image import image2text

#from generate_image import generate_image

class Test__post_images(unittest.TestCase):
    """Test RestApiV1 functions related to getting images"""
    
    def setUp(self):
        self.start_time = time.time()
        print(f"\nTest #{getattr(self, 'test_number', 'N/A')}: {self.__class__.__name__}.{self._testMethodName}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def tearDown(self):
        end_time = time.time()
        duration = end_time - self.start_time
        print(f"Test ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test duration: {duration:.2f} seconds")    
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.images_path = os.path.join(
                os.path.dirname(__file__),
                "images")
        cls.template_path = os.path.join(cls.images_path, "templates")
        cls.download_path = os.path.join(cls.images_path, "download")
        cls.upload_path = os.path.join(cls.images_path, "upload")
        shutil.rmtree(cls.download_path, ignore_errors=True)
        shutil.rmtree(cls.upload_path, ignore_errors=True)
        os.mkdir(cls.download_path)
        os.mkdir(cls.upload_path)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()   

    #----------------------------------------------------------------------------- 
    
    def test__post_hwitem_image(self):
        #{{{
        """Post an image for an item"""
        # print("\n=== Testing to post an image for an item ===")
        # print("POST /api/v1/components/{part_id}/images")

        part_id = "Z00100300006-00001"

        upload_file = generate_image(self.template_path, self.upload_path)
        upload_file_short = upload_file.split("/")[-1]

        data = {
            "comments": f"uploading {upload_file_short}",
        }            

        logger.info(data)

        resp = post_hwitem_image(part_id, data, upload_file)
    
        logger.info(f"response: {resp}")

        #TODO: Maybe go get it again and compare? See if comments appear?

        #}}} 

##################################################################################

def generate_image(template_path, destination_path, seed=None):

    if seed is not None:
        random.seed(seed)

    template = os.path.join(template_path, random.choice(os.listdir(template_path)))
    quote_top, quote_bottom = random.choice(quotes)

    dest_ext = template.split(".")[-1]
    dest_file = os.path.join(destination_path, 
                    f"image-{random.randint(0, 999999999):09d}.{dest_ext}")
    
    image = Image.open(template)
    w, h = image.size

    if w < 500:
        image = image.resize((500, 500 * h // w))
        w, h = image.size

    draw = ImageDraw.Draw(image)

    fontsize = w // 25 + 1
    shadow_offset = max(1, fontsize // 10)

    logger.info(f"fontsize: {fontsize}, shadow: {shadow_offset}")

    try:
        # Borrow a font from matplotlib, which should be on the system
        # if Python was installed via Anaconda.
        fontdir = os.path.join(os.path.dirname(mpl.__file__), "mpl-data", "fonts", "ttf")
        fontfile1 = os.path.join(fontdir, "DejaVuSans-BoldOblique.ttf")
        fontfile2 = os.path.join(fontdir, "DejaVuSans.ttf")
        
        #fontdir = os.path.join(os.path.dirname(__file__), "fonts")
        #fontfile1 = os.path.join(fontdir, "impact.ttf")
        #fontfile2 = os.path.join(fontdir, "impact.ttf")
        
        font1 = ImageFont.truetype(fontfile1, fontsize)
        font2 = ImageFont.truetype(fontfile2, fontsize//2)
    except Exception as err:
        logger.warning(f"error when trying to set font: {repr(err)}")    
        font1 = ImageFont.load_default()
        font2 = ImageFont.load_default()

    def shadow_text(text_offset, shadow_offset, text, anchor, align, font, fill):
        x_offset, y_offset = text_offset
        draw.multiline_text(
                (x_offset-shadow_offset, y_offset-shadow_offset),
                text,
                anchor=anchor, align=align, font=font,
                fill=0x00000000)
        draw.multiline_text(
                (x_offset+1, y_offset+1),
                text,
                anchor=anchor, align=align, font=font,
                fill=0x00000000)
        draw.multiline_text(
                (x_offset, y_offset),
                text,
                anchor=anchor, align=align, font=font,
                fill=fill)


    if quote_top is not None:
        shadow_text( (w//2, fontsize), shadow_offset,
                quote_top.upper(),
                anchor="ma", align="center", font=font1,
                fill=0xff77ffff)
    if quote_bottom is not None:
        shadow_text( (w//2, h-2*fontsize), shadow_offset,
                quote_bottom.upper(),
                anchor="md", align="center", font=font1,
                fill=0xff77ffff)

        timestr = datetime.datetime.now().astimezone().strftime("%Y-%b-%d %I:%M:%S%p (%z)")
        shadow_text( (w-fontsize//2, h-fontsize//4), 1,
                    f"generated {timestr}",
                    anchor="rd", align="right", font=font2,
                    fill=0xff777777)

    image.save(dest_file)
    return dest_file


quotes = \
[
    (None, "Do not be afraid of competition."),
    (None, "An exciting opportunity\nlies ahead of you"),
    (None, "You will always be surrounded\nby true friends."),
    (None, "You should be able to undertake\nand complete anything."),
    (None, "You are kind and friendly."),
    (None, "You are wise beyond your years."),
    (None, "Your ability to juggle many tasks\nwill take you far."),
    (None, "A routine task will turn\ninto an enchanting adventure."),
    ("Beware of all enterprises", "that require new clothes."),
    (None, "Be true to your work,\nyour word, and your friend."),
    ("A journey of a thousand miles", "begins with a single step"),
    ("Forget injuries", "never forget kindnesses"),
    (None, "Respect yourself\nand others will respect you."),
    (None, "A man cannot be comfortable\nwithout his own approval."),
    ("Always do right.", "This will gratify some people\nand astonish the rest"),
    ("It is easier to stay out", "than to get out"),
    (None, "Sing everyday\nand chase the mean blues away."),
    (None, "You will receive money\nfrom an unexpected source."),
    (None, "Attitude is a little thing\nthat makes a big difference."),
    (None, "Experience is the best teacher."),
    (None, "You will be happy\nwith your spouse."),
    (None, "Expect the unexpected."),
    ("Stay healthy", "Walk a mile"),
    ("The family that plays together", "stays together"),
    (None, "Eat chocolate to have\na sweeter life."),
    ("Once you make a decision", "the universe conspires\nto make it happen"),
    (None, "Make yourself necessary\nto someone."),
    ("The only way to have a friend", "is to be one"),
    ("Nothing great was ever achieved", "without enthusiasm"),
    (None, "Dance as if no one is watching."),
    (None, "Live this day as if\nit were your last."),
    (None, "Your life will be\nhappy and peaceful."),
    (None, "Reach for joy\nand all else will follow."),
    (None, "Move in the direction\nof your dreams."),
    (None, "Bloom where you are planted."),
    (None, "Appreciate. Appreciate. Appreciate."),
    (None, "Happy News is on its way."),
    ("If you can't be a good example", "you'll just have to be\na horrible warning"),
    ("Mathematicians deal with\nlarge numbers sometimes", "but never in their income"),
    ("Half the fun of the travel", "is the esthetic of lostness"),
    ("They muddy the water", "to make it seem deep"),
    (None, "The art of being wise is\nthe art of knowing\nwhat to overlook."),
    ("Do, or do not.", "There is no try"),
    (None, "Science and everyday life\ncannot and should not\nbe separated."),
    ("Today I will be happier", "than a bird\nwith a french fry."),
    ("Suffer the pain of discipline", "or suffer the pain of regret"),
    ("Dance the dance you dance", "Don't dance the dance\npeople who dance dance"),
    ("It is easier to build\nstrong children", "than to repair\nbroken men"),
    ("The love of knowledge", "is a kind of madness."),
    ("Yesterday", "you said tomorrow"),
    ("If it is important to you,\nyou will find a way", "If not,\nyou'll find an excuse"),
    ("Do unto others 20% better\nthan you would expect\nthem to do unto you",
            "to correct for subjective error"),
    ("We are all born ignorant", "but one must work hard\nto remain stupid."),
    ("Patience is not the ability to wait",
            "but the ability to keep\na good attitude while waiting"),
    ("You can do anything", "but not everything."),
    ("Even if I knew that tomorrow\nthe world would go to pieces",
            "I would still plant\nmy apple tree"),
    ("It's hard to be an artist.", "It's hard to be anything.\nIt's hard to be."),
    ("Time flies like an arrow", "fruit flies like a banana."),
    ("Don't take life too seriously.", "You'll never get\nout of it alive"),
    ("He who lives\nin harmony with himself", "lives in harmony\nwith the universe"),
    ("I would rather\ndie on my feet", "than live on my knees"),
    ("Everything is funny", "as long as it is happening\nto somebody else"),
    ("If you're going through hell", "keep going"),
    ("The best way to cheer yourself", "is to try to cheer\nsomeone else up"),
]

if __name__ == "__main__":
    unittest.main(argv=config.remaining_args)

