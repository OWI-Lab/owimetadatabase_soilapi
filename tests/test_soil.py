#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Bruno Stuyts'

# Native Python packages
import unittest
import os

# 3rd party packages
import pandas as pd
import numpy as np

# Project imports
from owimetadatabase_soilapi.soil.io import SoilAPI, SOIL_URL_PREFIX_STAGING

TESTS_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


class Test_data_retrieval(unittest.TestCase):

    """
    Class for unit testing behaviour of the soil data API wrapper.

    Assumes that data is present in the database staging website.
    """

    def setUp(self):
        TOKEN = os.getenv('GEOTECHDB_TOKEN')
        self.soil_api = SoilAPI(
            api_root=SOIL_URL_PREFIX_STAGING,
            header={'Authorization': 'Token %s' % (TOKEN)})

    def test_get_closest_location(self):
        """
        Test behaviour of wrapper for retrieval of closest location
        :return:
        """
        all_locations = self.soil_api.get_testlocations(project='HKN')['data']
        closest_bh = self.soil_api.get_closest_testlocation(
            latitude=all_locations[all_locations['title'] == 'HKN38-SCPT']['northing'].iloc[0],
            longitude=all_locations[all_locations['title'] == 'HKN38-SCPT']['easting'].iloc[0],
            title__contains='BH')
        self.assertEqual(closest_bh['title'], 'HKN39-BH-SA')

        closest_bh = self.soil_api.get_closest_testlocation(
            latitude=all_locations[all_locations['title'] == 'HKN38-SCPT']['northing'].iloc[0],
            longitude=all_locations[all_locations['title'] == 'HKN38-SCPT']['easting'].iloc[0],
            title__contains='TCPT')
        self.assertEqual(closest_bh['title'], 'HKN38-TCPT')

    def test_get_proximity_insitutests(self):
        """
        Test behaviour of wrapper for retrieval of closest in-situ test.
        Test with and without optional parameters
        :return:
        """
        closests_tests = self.soil_api.get_proximity_insitutests(
            latitude=51.707765, longitude=2.798876, radius=0.5
        )['data']
        closests_tests = self.soil_api.get_proximity_insitutests(
            latitude=51.707765, longitude=2.798876, radius=0.5,
            test_type__title="Seabed PCPT"
        )['data']

    def test_get_closest_insitutest(self):
        """
        Test retrieval of closest in-situ test with and without optional parameters
        :return:
        """
        result = self.soil_api.get_closest_insitutest(
            latitude=51.707765, longitude=2.798876, initialradius=0.5, target_srid='32631')
        self.assertEqual(result['title'], 'BH-102')
        result = self.soil_api.get_closest_insitutest(
            latitude=51.707765, longitude=2.798876, initialradius=0.5, target_srid='32631',
            test_type__title__icontains="Seabed")
        self.assertEqual(result['title'], result['title'])

    def test_get_closest_batchlabtest(self):
        closest = self.soil_api.get_closest_batchlabtest(
            latitude=51.707765, longitude=2.798876, initialradius=0.5, target_srid='32631',
            test_type__title__icontains="Atter")
        self.assertEqual(closest['title'], 'Atterberg')

    def test_get_closest_geotechnicalsample(self):
        geotechnicalsample = self.soil_api.get_closest_geotechnicalsample(
            latitude=51.672264, longitude=2.866408, radius=1, depth=10, top_depth__gte=10, bottom_depth__lte=20)
        self.assertEqual(geotechnicalsample['title'], '72BagA')

    def test_get_closest_sampletest(self):
        sampletest = self.soil_api.get_closest_sampletest(
            latitude=51.672264, longitude=2.866408, radius=1, depth=11, depth__gte=10, depth__lte=20)
        self.assertEqual(sampletest['title'], 'MRC1-2 - 100kPa')

    def test_get_closest_soilprofile(self):
        soilprofile = self.soil_api.get_closest_soilprofile(
            latitude=51.684798, longitude=2.785303, radius=1, title__contains='PISA BE')
        self.assertEqual(soilprofile['title'], 'PISA BE')

    def test_get_unit_insitutestdata(self):
        """
        Check correct behaviour of unit specific in-situ test retrieval
        """
        result = self.soil_api.get_unit_insitutestdata(
            soilunit="Wemmel sand",
            projectsite="Nobelwind",
            testtype="Downhole PCPT"
        )
        self.assertEqual(result.__len__(), 930)

    def test_get_unit_batchlabtestdata(self):
        """
        Check correct behaviour of unit-specific batch lab test data retrieval
        """
        result = self.soil_api.get_unit_batchlabtestdata(
            soilunit="Wemmel sand",
            depthcol="Depth [m]",
            projectsite="Nobelwind",
            testtype="Water content"
        )
        self.assertEqual(result.__len__(), 57)

    def test_get_unit_sampletests(self):
        """
        Check correct behaviour of unit-specific sample test data
        """
        result = self.soil_api.get_unit_sampletests(
            soilunit="Oedelem clay",
            projectsite="Nobelwind",
            testtype="Bender element"
        )
        self.assertEqual(result.__len__(), 1)