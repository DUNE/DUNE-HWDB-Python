#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2024 Regents of the University of Minnesota
Authors: 
    Alex Wagner <wagn0033@umn.edu>, Dept. of Physics and Astronomy
    Urbas Ekka <ekka0002@umn.edu>, Dept. of Physics and Astronomy

Test RestApiV1 functions related to getting images
"""

from Sisyphus.Utils import UnitTest as unittest
from Sisyphus.Configuration import config

import os, shutil
import json
import time
from datetime import datetime

from Sisyphus.RestApiV1 import get_hwitem
from Sisyphus.RestApiV1 import get_hwitem_image_list
from Sisyphus.RestApiV1 import get_component_type_image_list
from Sisyphus.RestApiV1 import get_image
from Sisyphus import RestApiV1 as ra

from Sisyphus.Utils.Terminal.Image import image2text

logger = config.getLogger(__name__)

class Test__get_images(unittest.TestCase):
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

        cls.download_path = os.path.join(
                os.path.dirname(__file__),
                "images", "download")
        shutil.rmtree(cls.download_path, ignore_errors=True)
        os.makedirs(cls.download_path)


    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()   

       
        # Uncomment the next line if you want it to delete the directory
        # after it's done. 
        
        # shutil.rmtree(cls.download_path)

    #----------------------------------------------------------------------------- 
    
    def test__get_component_type_image_list(self):
        """Get a list of images stored for a component type"""
        print("\n=== Testing to get a list of images stored for a component type ===")
        print("GET /api/v1/component-types/{part_type_id}/images")
        print("Retrieving images for part_type_id: Z00100300006")

        expected_fields = {
            "comments", "created", "creator", "image_id", "image_name",
            "library", "link"
        }

        try:
            resp = get_component_type_image_list("Z00100300006")

            # We'll only test that there's at least one image, and that
            # we don't raise an exception when we fetch it.             
            self.assertEqual(resp["status"], "OK")
            self.assertGreater(len(resp["data"]), 0)
            for image_node in resp["data"]:
                self.assertSetEqual(set(image_node.keys()), expected_fields)
                image_name = os.path.join(self.download_path, image_node["image_name"])
                resp = get_image(image_node["image_id"], write_to_file=image_name)
                textimage = image2text(resp.content, columns=40)
                logger.info("\n" + textimage)
                break

        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err 
    
    #----------------------------------------------------------------------------- 
    
    def test__get_hwitem_image_list(self):
        """Get a list of images stored for an item"""
        print("\n=== Testing to get a list of images stored for an item ===")
        print("GET /api/v1/components/{part_id}/images")
        print("Retrieving images for part_id: Z00100300006-00001")

        expected_fields = {
            "comments", "created", "creator", "image_id", "image_name",
            "library", "link"
        }

        try:
            resp = get_hwitem_image_list("Z00100300006-00001")

            # We'll only test that there's at least one image, and that
            # we don't raise an exception when we fetch it.             
            self.assertEqual(resp["status"], "OK")
            self.assertGreater(len(resp["data"]), 0)
            for image_node in resp["data"]:
                self.assertSetEqual(set(image_node.keys()), expected_fields)
                image_name = os.path.join(self.download_path, image_node["image_name"])
                resp = get_image(image_node["image_id"], write_to_file=image_name)
                textimage = image2text(resp.content, columns=40)
                logger.info("\n" + textimage)
                break

        except AssertionError as err:
            logger.error(f"Assertion Error: {repr(err)}")
            logger.info(f"server response:\n{json.dumps(resp, indent=4)}")
            raise err 
    
##############################################################################                                
if __name__ == "__main__":
    unittest.main(argv=config.remaining_args)