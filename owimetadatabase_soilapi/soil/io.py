# -*- coding: utf-8 -*-

__author__ = 'Bruno Stuyts'

# Native Python packages
import json
import warnings
from copy import deepcopy

# 3rd party packages
import pandas as pd
import numpy as np
import requests
from groundhog.siteinvestigation.insitutests.pcpt_processing import PCPTProcessing, plot_longitudinal_profile, \
    plot_combined_longitudinal_profile
from groundhog.general.soilprofile import profile_from_dataframe, plot_fence_diagram
from groundhog.general.parameter_mapping import offsets
import plotly.express as px
from pyproj import Transformer

# Project imports
from owimetadatabase_soilapi.io import API

SOIL_URL_PREFIX = "https://owimetadatabase.owilab.be/api/v1/soildata"


class SoilAPI(API):
    """
    Class to connect to the soil data API.

    A number of methods are provided to query the database via the database API.
    In the majority of cases, the methods return a dataframe based on the URL parameters provided.
    The methods are written such that a number of mandatory URL parameters are required (see documentation of the methods).
    The URL parameters can be expanded with Django-style additional filtering arguments (e.g. ``location__title__icontains="BB"``) as optional keyword arguments. Knowledge of the Django models is required for this.
    """

    @staticmethod
    def urlparameters(parameters, parameternames):
        """
        Returns a dictionary with URL parameters based on lists of parameters and parameter names
        
        :param parameters: List with parameters
        :param parameternames: List with parameter names
        
        :return: Dictionary with the URL parameters
        """
        url_params = {}

        for param, paramname in zip(parameters, parameternames):
            url_params[paramname] = param

        return url_params

    def get_proximity_entities_2d(self, api_url, latitude, longitude, radius, **kwargs):
        """
        Find the entities in a certain radius around a point in 2D (cylindrical search area)
        
        :param api_url: URL of the endpoint
        :param latitude: Latitude of the central point in decimal format
        :param longitude: Longitude of the central point in decimal format
        :param radius: Initial search radius around the central point in km
        :param kwargs: Optional keyword arguments for the search
        
        :return:
        """
        geosearch_params = dict(
            latitude=latitude,
            longitude=longitude,
            offset=radius
        )
        url_params = {**geosearch_params, **kwargs}

        resp = requests.get(
            url='%s/%s/' % (self.api_root, api_url),
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df,
            'exists': exists
        }

    def get_closest_entity_2d(self, api_url, latitude, longitude, initialradius=1, target_srid='25831', **kwargs):
        """
        Get the entity closest to a certain point in 2D with optional query arguments (cylindrical search area)
        
        :param api_url: End-point for the API
        :param latitude: Latitude of the central point in decimal format
        :param longitude: Longitude of the central point in decimal format
        :param initialradius: Initial search radius around the central point in km, the search radius is increased until locations are found
        :param target_srid: SRID for the offset calculation in meters
        :param kwargs: Optional keyword arguments e.g. ``campaign__projectsite__title__icontains='HKN'``
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the test location data for each location in the specified search area
            - 'id': ID of the closest test location
            - 'title': Title of the closest test location
            - 'offset [m]': Offset in meters from the specified point
        """

        radius = initialradius
        while True:
            geosearch_params = dict(
                latitude=latitude,
                longitude=longitude,
                offset=radius
            )
            url_params = {**geosearch_params, **kwargs}

            resp = requests.get(
                url='%s/%s/' % (self.api_root, api_url),
                headers=self.header,
                params=url_params)

            try:
                df = pd.DataFrame(json.loads(resp.text))
            except:
                warnings.warn("Response could not be loaded. This is most likely because no data was returned")
                df = pd.DataFrame()

            if df.__len__() != 0:
                break
            warnings.warn("Expanding search radius to")
            radius = 2 * radius
            warnings.warn("Expanding search radius to %.1fkm" % radius)


        transformer = Transformer.from_crs('epsg:4326', 'epsg:%s' % target_srid)
        df['easting [m]'], df['northing [m]'] = transformer.transform(
            np.array(df['easting']),
            np.array(df['northing']))

        point_east, point_north = transformer.transform(
            longitude,
            latitude)

        df['offset [m]'] = np.sqrt(
            (df['easting [m]'] - point_east) ** 2 +
            (df['northing [m]'] - point_north) ** 2)

        if df.__len__() == 1:
            loc_id = df['id'].iloc[0]
        else:
            df.sort_values('offset [m]', inplace=True)
            loc_id = df[df['offset [m]'] == df['offset [m]'].min()]['id'].iloc[0]

        return {
            'data': df,
            'id': loc_id,
            'title': df['title'].iloc[0],
            'offset [m]': df[df['offset [m]'] == df['offset [m]'].min()]['offset [m]'].iloc[0]
        }

    def get_closest_entity_3d(self, api_url, latitude, longitude, depth, initialradius=1, target_srid='25831',
                              sampletest=True, **kwargs):
        """
        Get the entity closest to a certain point in 3D (spherical search area) with optional query arguments
        
        :param api_url: End-point for the API
        :param latitude: Latitude of the central point in decimal format
        :param longitude: Longitude of the central point in decimal format
        :param depth of the central point in meters below seabed
        :param initialradius: Initial search radius around the central point in km, the search radius is increased until locations are found
        :param target_srid: SRID for the offset calculation in meters
        :param sampletest: Boolean indicating whether a sample or sample test needs to be retrieved (default is True to search for sample tests)
        :param kwargs: Optional keyword arguments e.g. ``campaign__projectsite__title__icontains='HKN'``
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the test location data for each location in the specified search area
            - 'id': ID of the closest test location
            - 'title': Title of the closest test location
            - 'offset [m]': Offset in meters from the specified point
        """

        radius = initialradius
        while True:
            geosearch_params = dict(
                latitude=latitude,
                longitude=longitude,
                offset=radius
            )
            url_params = {**geosearch_params, **kwargs}

            resp = requests.get(
                url='%s/%s/' % (self.api_root, api_url),
                headers=self.header,
                params=url_params)

            try:
                df = pd.DataFrame(json.loads(resp.text))
            except:
                warnings.warn("Response could not be loaded. This is most likely because no data was returned")
                df = pd.DataFrame()

            if df.__len__() != 0:
                break
            warnings.warn("Expanding search radius to")
            radius = 2 * radius
            warnings.warn("Expanding search radius to %.1fkm" % radius)


        transformer = Transformer.from_crs('epsg:4326', 'epsg:%s' % target_srid)
        df['easting [m]'], df['northing [m]'] = transformer.transform(
            np.array(df['easting']),
            np.array(df['northing']))

        point_east, point_north = transformer.transform(
            longitude,
            latitude)

        if not sampletest:
            df['depth'] = 0.5 * (df['top_depth'] + df['bottom_depth'])

        df['offset [m]'] = np.sqrt(
            (df['easting [m]'] - point_east) ** 2 +
            (df['northing [m]'] - point_north) ** 2 +
            (df['depth'] - depth) ** 2
        )

        if df.__len__() == 1:
            loc_id = df['id'].iloc[0]
        else:
            df.sort_values('offset [m]', inplace=True)
            loc_id = df[df['offset [m]'] == df['offset [m]'].min()]['id'].iloc[0]

        return {
            'data': df,
            'id': loc_id,
            'title': df['title'].iloc[0],
            'offset [m]': df[df['offset [m]'] == df['offset [m]'].min()]['offset [m]'].iloc[0]
        }

    def get_surveycampaigns(self, projectsite=None, **kwargs):
        """
        Get all available survey campaigns, specify a projectsite to filter by projectsite
        
        :param projectsite: String with the projectsite title (e.g. "HKN")
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the location data for each location in the projectsite
            - 'exists': Boolean indicating whether matching records are found
        """
        url_params = self.urlparameters(
            parameters=[projectsite, ],
            parameternames=['projectsite', ]
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/surveycampaign/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df,
            'exists': exists
        }

    def get_surveycampaign_detail(self, projectsite=None, campaign=None, **kwargs):
        """
        Get a selected survey campaign
        
        :param projectsite: Name of the projectsite (e.g. "HKN")
        :param campaign: Title of the survey campaign (e.g. "Borehole campaign")
        
        :return: Dictionary with the following keys:
        
            - 'id': id of the selected projectsite site
            - 'data': Pandas dataframe with the location data for the individual location
            - 'exists': Boolean indicating whether a matching location is found
        """
        url_params = self.urlparameters(
            parameters=[projectsite, campaign],
            parameternames=['projectsite', 'campaign']
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/surveycampaign/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            exists = False
            campaign_id = None
        elif df.__len__() == 1:
            exists = True
            campaign_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one survey campaign was returned, check search criteria.")

        return {
            'id': campaign_id,
            'data': df,
            'exists': exists
        }

    def surveycampaign_exists(self, projectsite=None, campaign=None, **kwargs):
        """
        Checks if the survey campaign answering to the search criteria exists

        :param projectsite: Name of the projectsite under consideration (e.g. "HKN")
        :param campaign: Name of the survey campaign (optional, default is None to return all locations in a projectsite)
        
        :return: Returns the id if survey campaign exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[projectsite, campaign],
            parameternames=['projectsite', 'campaign']
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/surveycampaign/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            record_id = False
        elif df.__len__() == 1:
            record_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one survey campaign was returned, refine search criteria")

        return record_id

    def get_proximity_testlocations(self, latitude, longitude, radius, **kwargs):
        """
        Get all soil test locations in a certain radius surrounding a point with given lat/lon
        
        :param latitude: Latitude of the central point in decimal format
        :param longitude: Longitude of the central point in decimal format
        :param radius: Radius around the central point in km
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the test location data for each location in the specified search area
            - 'exists': Boolean indicating whether matching records are found
        """
        return self.get_proximity_entities_2d(
            api_url='testlocationproximity',
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            **kwargs)

    def get_closest_testlocation(self, latitude, longitude, initialradius=1, target_srid='25831', **kwargs):
        """
        Get the soil test location closest to a certain point with the name containing a certain string
        
        :param latitude: Latitude of the central point in decimal format
        :param longitude: Longitude of the central point in decimal format
        :param initialradius: Initial search radius around the central point in km, the search radius is increased until locations are found
        :param target_srid: SRID for the offset calculation in meters
        :param kwargs: Optional keyword arguments e.g. ``campaign__projectsite__title__icontains='HKN'``
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the test location data for each location in the specified search area
            - 'id': ID of the closest test location
            - 'title': Title of the closest test location
            - 'offset [m]': Offset in meters from the specified point
        """
        return self.get_closest_entity_2d(
            api_url='testlocationproximity',
            latitude=latitude,
            longitude=longitude,
            initialradius=initialradius,
            target_srid=target_srid,
            **kwargs
        )

    def get_testlocations_profile(self, lat1, lon1, lat2, lon2, band=1000):
        """
        Retrieves test locations along a profile line
        
        :param lat1: Latitude of the start point
        :param lon1: Longitude of the start point
        :param lat2: Latitude of the end point
        :param lon2: Longitude of the end point
        :param band: Thickness of the band (in m, default=1000m)
        
        :return: Returns a dataframe with the summary data of the selected in-situ tests
        """
        resp = requests.get(
            url='%s/testlocationprofile/' % self.api_root,
            headers=self.header,
            params={
                'lat1': lat1,
                'lon1': lon1,
                'lat2': lat2,
                'lon2': lon2,
                'offset': band
            })
        try:
            return pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            return pd.DataFrame()

    def get_testlocations(self, projectsite=None, campaign=None, location=None, **kwargs):
        """
        Get the geotechnical test locations corresponding to the given search criteria
        
        :param projectsite: Name of the projectsite under consideration (e.g. "HKN")
        :param campaign: Name of the survey campaign (optional, default is None to return all locations in a projectsite)
        :param location: Name of a specific location (optional, default is None to return all locations in a projectsite)
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the test location data for each location meeting the specified search criteria
            - 'exists': Boolean indicating whether matching records are found
        """
        url_params = {}

        for param, paramname in zip([projectsite, campaign, location],
                                    ['projectsite', 'campaign', 'location']):
            url_params[paramname] = param

        url_params = {**url_params, **kwargs}

        resp_testlocations = requests.get(
            url='%s/testlocation/' % self.api_root,
            headers=self.header,
            params=url_params)
        df = pd.DataFrame(json.loads(resp_testlocations.text))

        if df.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df,
            'exists': exists
        }

    def get_testlocation_detail(self, projectsite=None, location=None, campaign=None, **kwargs):
        """
        Get the detailed information for a geotechnical test location
        
        :param projectsite: Name of the projectsite under consideration (e.g. "HKN")
        :param campaign: Name of the survey campaign (optional, default is None to return all locations in a projectsite)
        :param location: Name of a specific location (optional, default is None to return all locations in a projectsite)
        
        :return: Dictionary with the following keys:
        
            - 'id': id of the selected test location
            - 'data': Pandas dataframe with the test location data for each location meeting the specified search criteria
            - 'exists': Boolean indicating whether matching records are found
        """
        url_params = self.urlparameters(
            parameters=[projectsite, campaign, location],
            parameternames=['projectsite', 'campaign', 'location']
        )

        url_params = {**url_params, **kwargs}

        resp_testlocations = requests.get(
            url='%s/testlocation/' % self.api_root,
            headers=self.header,
            params=url_params)
        df = pd.DataFrame(json.loads(resp_testlocations.text))

        if df.__len__() == 0:
            exists = False
            id = None
        elif df.__len__() == 1:
            exists = True
            id = df['id'].iloc[0]
        else:
            raise ValueError("More than one test location was returned, refine search criteria")

        return {
            'id': id,
            'data': df,
            'exists': exists
        }

    def testlocation_exists(self, projectsite=None, location=None, campaign=None, **kwargs):
        """
        Checks if the test location answering to the search criteria exists

        :param projectsite: Name of the projectsite under consideration (e.g. "HKN")
        :param campaign: Name of the survey campaign (optional, default is None to return all locations in a projectsite)
        :param location: Name of a specific location (optional, default is None to return all locations in a projectsite)

        :return: Returns the id if test location exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[projectsite, campaign, location],
            parameternames=['projectsite', 'campaign', 'location']
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/testlocation/' % self.api_root,
            headers=self.header,
            params=url_params)
        
        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            record_id = False
        elif df.__len__() == 1:
            record_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one test location was returned, refine search criteria")

        return record_id

    def plot_testlocations(self, return_fig=False, **kwargs):
        """
        Retrieves soil test locations and generates a Plotly plot to show them
        
        :param return_fig: Boolean indicating whether the Plotly figure object needs to be returned (default is False which simply shows the plot)
        :param kwargs: Keyword arguments for the search (see ``get_testlocations``)
        
        :return: Plotly figure object with selected asset locations plotted on OpenStreetMap tiles (if requested)
        """
        testlocations = self.get_testlocations(**kwargs)['data']
        fig = px.scatter_mapbox(testlocations, lat='northing', lon="easting", hover_name="title",
                                hover_data=["projectsite_name", "description"],
                                zoom=10, height=500)
        fig.update_layout(mapbox_style="open-street-map")
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        if return_fig:
            return fig
        else:
            fig.show()

    def get_insitutests(self, projectsite=None, location=None, testtype=None, insitutest=None, **kwargs):
        """
        Get the detailed information (measurement data) for an in-situ test of give type
        
        :param projectsite: Name of the projectsite (e.g. "HKN")
        :param location: Name of the test location (e.g. "HKN75-SCPT-A")
        :param testtype: Name of the test type (e.g. "S-PCPT")
        :param insitutest: Name of the in-situ test

        :return: Dictionary with the following keys:
        
            - 'data': Metadata of the insitu tests
            - 'exists': Boolean indicating whether a matching in-situ test is found
        """
        url_params = self.urlparameters(
            parameters=[projectsite, location, testtype, insitutest],
            parameternames=['projectsite', 'location', 'testtype', 'insitutest']
        )

        url_params = {**url_params, **kwargs}

        resp_summary = requests.get(
            url='%s/insitutestsummary/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df_summary = pd.DataFrame(json.loads(resp_summary.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df_summary,
            'exists': exists
        }

    def get_proximity_insitutests(self, latitude, longitude, radius, **kwargs):
        """
        Get all in-situ tests in a certain radius surrounding a point with given lat/lon
        
        :param latitude: Latitude of the central point in decimal format
        :param longitude: Longitude of the central point in decimal format
        :param radius: Radius around the central point in km
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the in-situ test summary data for each in-situ test in the specified search area
            - 'exists': Boolean indicating whether matching records are found
        """
        return self.get_proximity_entities_2d(
            api_url='insitutestproximity',
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            **kwargs)

    def get_closest_insitutest(self, latitude, longitude, initialradius=1, target_srid='25831', **kwargs):
        """
        Get the in-situ test closest to a certain point with the name containing a certain string
        
        :param latitude: Latitude of the central point in decimal format
        :param longitude: Longitude of the central point in decimal format
        :param initialradius: Initial search radius around the central point in km, the search radius is increased until locations are found
        :param target_srid: SRID for the offset calculation in meters
        :param kwargs: Optional keyword arguments e.g. ``campaign__projectsite__title__icontains='HKN'``
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the in-situ test data for each in-situ test in the specified search area
            - 'id': ID of the closest in-situ test
            - 'title': Title of the closest in-situ test
            - 'offset [m]': Offset in meters from the specified point
        """
        return self.get_closest_entity_2d(
            api_url='insitutestproximity',
            latitude=latitude,
            longitude=longitude,
            initialradius=initialradius,
            target_srid=target_srid,
            **kwargs
        )

    def get_insitutesttypes(self, testtype=None, **kwargs):
        """
        Find all in-situ test types corresponding to the search parameters
        
        :return: Dictionary with the following keys:
        
            - 'data': Dataframe with the in-situ test types returned from the query
            - 'exists': Boolean containing whether data is in the returned query
        """
        url_params = self.urlparameters(
            parameters=[testtype,],
            parameternames=['testtype',]
        )

        url_params = {**url_params, **kwargs}

        resp_summary = requests.get(
            url='%s/insitutesttype/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df_summary = pd.DataFrame(json.loads(resp_summary.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df_summary,
            'exists': exists
        }

    def insitutesttype_exists(self, testtype=None, **kwargs):
        """
        Checks if the in-situ test type answering to the search criteria exists

        :param testtype: Name of the test type (e.g. "PCPT")
        
        :return: Returns the id if the in-situ test type exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[testtype,],
            parameternames=['testtype',]
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/insitutesttype/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            record_id = False
        elif df.__len__() == 1:
            record_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one in-situ test type was returned, refine search criteria")

        return record_id


    def get_insitutest_detail(self, projectsite=None, location=None, testtype=None, insitutest=None,
                              combine=False, **kwargs):
        """
        Get the detailed information (measurement data) for an in-situ test of give type
        
        :param projectsite: Name of the projectsite (e.g. "HKN")
        :param location: Name of the test location (e.g. "HKN75-SCPT-A")
        :param testtype: Name of the test type (e.g. "PCPT")
        :param insitutest: Name of the in-situ test
        :param combine: Boolean indicating whether raw and processed data needs to be combined (default=False). If true, processed data columns are appended to the rawdata dataframe
        :param kwargs: Optional keyword arguments for further queryset filtering based on model attributes.

        :return: Dictionary with the following keys:
        
            - 'id': id of the selected test
            - 'insitutestsummary': Metadata of the insitu tests
            - 'rawdata': Raw data
            - 'processed': Processed data
            - 'conditions': Test conditions
            - 'response': Response text
            - 'exists': Boolean indicating whether a matching in-situ test is found
        """
        url_params = self.urlparameters(
            parameters=[projectsite, location, testtype, insitutest],
            parameternames=['projectsite', 'location', 'testtype', 'insitutest']
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/insitutestsummary/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df_summary = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
            id = None
        elif df_summary.__len__() == 1:
            exists = True
        else:
            raise ValueError("More than one in-situ test was returned, refine your search parameters.")

        resp_detail = requests.get(
            url='%s/insitutestdetail/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df_resp_detail = pd.DataFrame(json.loads(resp_detail.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_resp_detail = pd.DataFrame()

        id = df_resp_detail['id'].iloc[0]
        try:
            df_raw = pd.DataFrame(df_resp_detail['rawdata'].iloc[0]).reset_index(drop=True)
        except Exception as err:
            warnings.warn("Raw data could not be loaded. This is most likely because no data was returned")
            df_raw = pd.DataFrame()
        try:
            df_processed = pd.DataFrame(df_resp_detail['processeddata'].iloc[0]).reset_index(drop=True)
        except:
            warnings.warn("Processed data could not be loaded. This is most likely because no data was returned")
            df_processed = pd.DataFrame()
        try:
            df_conditions = pd.DataFrame(df_resp_detail['conditions'].iloc[0]).reset_index(drop=True)
        except:
            warnings.warn("Test conditions could not be loaded. This is most likely because no data was returned")
            df_conditions = pd.DataFrame()

        for _df in [df_raw, df_processed, df_conditions]:
            for col in _df.columns:
                try:
                    _df[col] = pd.to_numeric(_df[col], errors='ignore')
                except Exception as err:
                    warnings.warn(str(err))

        # Merge raw and processed cpt data
        if combine:
            try:
                df_raw = pd.merge(df_raw, df_processed, how='inner', on='z [m]', suffixes=["", "_processed"])
            except Exception as err:
                warnings.warn("ERROR: Combining raw and processed data failed - %s" % str(err))

        return_dict = {
            'id': id,
            'insitutestsummary': df_summary,
            'rawdata': df_raw,
            'processed': df_processed,
            'conditions': df_conditions,
            'response': resp_detail,
            'exists': exists
        }

        return return_dict

    def get_cpttest_detail(self, projectsite=None, location=None, testtype=None, insitutest=None, combine=False, cpt=True,
                              **kwargs):
        """
        Get the detailed information (measurement data) for an in-situ test of CPT type (seabed or downhole CPT)
        
        :param projectsite: Name of the projectsite (e.g. "HKN")
        :param location: Name of the test location (e.g. "HKN75-SCPT-A")
        :param testtype: Name of the test type (e.g. "PCPT")
        :param insitutest: Name of the in-situ test
        :param combine: Boolean indicating whether raw and processed data needs to be combined (default=False). If true, processed data columns are appended to the rawdata dataframe
        :param cpt: Boolean determining whether the in-situ test is a CPT or not. If True (default), a PCPTProcessing object is returned.
        :param kwargs: Optional keyword arguments for the cpt data loading. Note that further queryset filtering based on model attributes is not possible with this method. The in-situ test needs to be fully defined by the required arguments.

        :return: Dictionary with the following keys:
        
            - 'id': id of the selected test
            - 'insitutestsummary': Metadata of the insitu tests
            - 'rawdata': Raw data
            - 'processed': Processed data
            - 'conditions': Test conditions
            - 'response': Response text
            - 'cpt': PCPTProcessing object (only if the CPT data is successfully loaded)
            - 'exists': Boolean indicating whether a matching in-situ test is found
        """
        url_params = self.urlparameters(
            parameters=[projectsite, location, testtype, insitutest],
            parameternames=['projectsite', 'location', 'testtype', 'insitutest']
        )

        resp_summary = requests.get(
            url='%s/insitutestsummary/' % self.api_root,
            headers=self.header,
            params=url_params)
        
        try:
            df_summary = pd.DataFrame(json.loads(resp_summary.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
            id = None
        elif df_summary.__len__() == 1:
            exists = True
        else:
            raise ValueError("More than one in-situ test was returned, refine your search parameters.")

        resp_detail = requests.get(
            url='%s/insitutestdetail/' % self.api_root,
            headers=self.header,
            params=url_params)
        df_resp_detail = pd.DataFrame(json.loads(resp_detail.text))
        id = df_resp_detail['id'].iloc[0]
        try:
            df_raw = pd.DataFrame(df_resp_detail['rawdata'].iloc[0]).reset_index(drop=True)
        except Exception as err:
            warnings.warn("Raw data could not be loaded. This is most likely because no data was returned")
            df_raw = pd.DataFrame()
        try:
            df_processed = pd.DataFrame(df_resp_detail['processeddata'].iloc[0]).reset_index(drop=True)
        except:
            warnings.warn("Processed data could not be loaded. This is most likely because no data was returned")
            df_processed = pd.DataFrame()
        try:
            df_conditions = pd.DataFrame(df_resp_detail['conditions'].iloc[0]).reset_index(drop=True)
        except:
            warnings.warn("Test conditions could not be loaded. This is most likely because no data was returned")
            df_conditions = pd.DataFrame()

        for _df in [df_raw, df_processed, df_conditions]:
            for col in _df.columns:
                try:
                    _df[col] = pd.to_numeric(_df[col], errors='ignore')
                except Exception as err:
                    warnings.warn(str(err))

        # Merge raw and processed cpt data
        if combine:
            try:
                df_raw = pd.merge(df_raw, df_processed, how='inner', on='z [m]', suffixes=["", "_processed"])
            except Exception as err:
                warnings.warn("ERROR: Combining raw and processed data failed - %s" % str(err))

        return_dict = {
            'id': id,
            'insitutestsummary': df_summary,
            'rawdata': df_raw,
            'processed': df_processed,
            'conditions': df_conditions,
            'response': resp_detail,
            'exists': exists
        }

        if cpt:
            try:
                cpt = PCPTProcessing(title=df_summary['title'].iloc[0])
                if 'Push' in df_raw.keys():  # Check if a key for the push is available (only for downhole CPTs)
                    push_key = 'Push'
                else:
                    push_key = None
                cpt.load_pandas(df_raw, push_key=push_key, **kwargs)  # Load the data into the PCPTProcessing object
                return_dict['cpt'] = cpt
            except Exception as err:
                warnings.warn("ERROR: PCPTProcessing object not created - %s" % str(err))

        return return_dict

    def insitutest_exists(self, projectsite=None, location=None, testtype=None, insitutest=None, **kwargs):
        """
        Checks if the in-situ test answering to the search criteria exists

        :param projectsite: Name of the projectsite (e.g. "HKN")
        :param location: Name of the test location (e.g. "HKN75-SCPT-A")
        :param testtype: Name of the test type (e.g. "PCPT")
        :param insitutest: Name of the in-situ test

        :return: Returns the id if the in-situ test exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[projectsite, location, testtype, insitutest],
            parameternames=['projectsite', 'location', 'testtype', 'insitutest']
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/insitutestdetail/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            record_id = False
        elif df.__len__() == 1:
            record_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one in-situ test was returned, refine search criteria")

        return record_id

    def get_soilprofiles(self, projectsite=None, location=None, soilprofile=None, **kwargs):
        """
        Retrieves soil profiles corresponding to the search criteria

        :param projectsite: Name of the projectsite (e.g. "HKN")
        :param location: Name of the test location (e.g. "HKN75-SCPT-A")
        :param soilprofile: Title of the soil profile (e.g. "Borehole log")

        :return: Dictionary with the following keys:
        
            - 'data': Metadata for the soil profiles
            - 'exists': Boolean indicating whether a matching in-situ test is found
        """

        url_params = {**self.urlparameters(
            parameters=[projectsite, location, soilprofile],
            parameternames=['projectsite', 'location', 'soilprofile']
            ), **kwargs}

        resp_summary = requests.get(
            url='%s/soilprofilesummary/' % self.api_root,
            headers=self.header,
            params=url_params)
        
        try:
            df_summary = pd.DataFrame(json.loads(resp_summary.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df_summary,
            'exists': exists
        }

    def get_proximity_soilprofiles(self, latitude, longitude, radius, **kwargs):
        """
        Get all soil profiles in a certain radius surrounding a point with given lat/lon
        
        :param latitude: Latitude of the central point in decimal format
        :param longitude: Longitude of the central point in decimal format
        :param radius: Radius around the central point in km
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the soil profile summary data for each soil profile in the specified search area
            - 'exists': Boolean indicating whether matching records are found
        """
        return self.get_proximity_entities_2d(
            api_url='soilprofileproximity',
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            **kwargs)

    def get_closest_soilprofile(self, latitude, longitude, initialradius=1, target_srid='25831', **kwargs):
        """
        Get the soil profile closest to a certain point with additional conditions as optional keyword arguments
        
        :param latitude: Latitude of the central point in decimal format
        :param longitude: Longitude of the central point in decimal format
        :param initialradius: Initial search radius around the central point in km, the search radius is increased until locations are found
        :param target_srid: SRID for the offset calculation in meters
        :param kwargs: Optional keyword arguments e.g. ``location__title__icontains='HKN'``
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the soil profile data for each soil profile in the specified search area
            - 'id': ID of the closest in-situ test
            - 'title': Title of the closest in-situ test
            - 'offset [m]': Offset in meters from the specified point
        """
        return self.get_closest_entity_2d(
            api_url='soilprofileproximity',
            latitude=latitude,
            longitude=longitude,
            initialradius=initialradius,
            target_srid=target_srid,
            **kwargs
        )

    def get_soilprofile_detail(self, projectsite=None, location=None, soilprofile=None, convert_to_profile=True,
                               profile_title=None, drop_info_cols=False, **kwargs):
        """
        Retrieves a soil profile from the database and converts it to a groundhog SoilProfile object

        :param projectsite: Name of the projectsite (e.g. "HKN")
        :param location: Name of the test location (e.g. "HKN75-SCPT-A")
        :param soilprofile: Title of the soil profile (e.g. "Borehole log")
        :param designiteration: Name of the design iteration (e.g. "FEED design")
        :param convert_to_profile: Boolean determining whether the soil profile needs to be converted to a groundhog SoilProfile object
        :param drop_info_cols: Boolean determining whether or not to drop the columns with additional info (e.g. soil description, ...). Default=False
        
        :return: Dictionary with the following keys:
        
            - 'id': id for the selected soil profile
            - 'soilprofilesummary': Metadata for the soil profile
            - 'response': Response text
            - 'soilprofile': Groundhog SoilProfile object (only if successfully processed)
            - 'exists': Boolean indicating whether a matching in-situ test is found
        """

        url_params = self.urlparameters(
            parameters=[projectsite, location, soilprofile],
            parameternames=['projectsite', 'location', 'soilprofile']
        )

        url_params = {**url_params, **kwargs}

        resp_summary = requests.get(
            url='%s/soilprofilesummary/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df_summary = pd.DataFrame(json.loads(resp_summary.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
            id = None
        elif df_summary.__len__() == 1:
            exists = True
        else:
            raise ValueError("More than one soil profile was returned, refine your search parameters.")

        resp_detail = requests.get(
            url='%s/soilprofiledetail/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df_resp_detail = pd.DataFrame(json.loads(resp_detail.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_resp_detail = pd.DataFrame()

        id = df_resp_detail['id'].iloc[0]

        return_dict = {
            'id': id,
            'soilprofilesummary': df_summary,
            'response': resp_detail,
            'exists': exists
        }

        if convert_to_profile:
            try:
                soilprofile_df = pd.DataFrame(
                    df_resp_detail['soillayer_set'].iloc[0]).sort_values('start_depth').reset_index(drop=True)
                soilprofile_df.rename(columns={
                    'start_depth': "Depth from [m]",
                    'end_depth': 'Depth to [m]',
                    'soiltype_name': 'Soil type',
                    'totalunitweight': 'Total unit weight [kN/m3]'
                }, inplace=True)

                for i, row in soilprofile_df.iterrows():
                    try:
                        for key, value in row['soilparameters'].items():
                            soilprofile_df.loc[i, key] = value
                    except:
                        pass
                if profile_title is None:
                    profile_title = "%s - %s" % (
                        df_summary['location_name'].iloc[0],
                        df_summary['title'].iloc[0],
                    )

                if drop_info_cols:
                    soilprofile_df.drop(
                        ['id', 'profile', 'soilparameters', 'soilprofile_name', 'soilunit', 'description', 'soilunit_name'],
                        axis=1, inplace=True)

                dsp = profile_from_dataframe(soilprofile_df, title=profile_title)
                return_dict['soilprofile'] = dsp

            except Exception as err:
                warnings.warn("Error during loading of soil layers and parameters for %s - %s" % (
                    df_summary['title'].iloc[0], str(err)))

        return return_dict

    def soilprofile_exists(self, projectsite=None, location=None, soilprofile=None, **kwargs):
        """
        Checks if the in-situ test answering to the search criteria exists

        :param projectsite: Name of the projectsite (e.g. "HKN")
        :param location: Name of the test location (e.g. "HKN75-SCPT-A")
        :param soilprofile: Title of the soil profile (e.g. "HKN75-SCPT-A")

        :return: Returns the id if soil profile exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[projectsite, location, soilprofile],
            parameternames=['projectsite', 'location', 'soilprofile']
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/soilprofiledetail/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            record_id = False
        elif df.__len__() == 1:
            record_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one soil profile was returned, refine search criteria")

        return record_id

    def soiltype_exists(self, soiltype=None, **kwargs):
        """
        Check if a soiltype with a given name exists

        :param soiltype: Name of the soil type
        
        :return: id of the soil type if it exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[soiltype,],
            parameternames=['soiltype',]
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/soiltype/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            record_id = False
        elif df.__len__() == 1:
            record_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one soil type was returned, refine search criteria")

        return record_id

    def get_soiltypes(self, **kwargs):
        """
        Find all soil types corresponding to the search parameters
        
        :return: Dictionary with the following keys:
        
            - 'data': Dataframe with the soil units returned from the query
            - 'exists': Boolean containing whether data is in the returned query
        """
        url_params = {}

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/soiltype/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df_summary = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df_summary,
            'exists': exists
        }

    def soilunit_exists(self, projectsite=None, soiltype=None, soilunit=None, **kwargs):
        """
        Check if a certain soil unit exists
        
        :param projectsite: Name of the project site
        :param soiltype: Name of the soil type
        :param soilunit: Name of the soil unit
        
        :return: id of the soil unit if it exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[projectsite, soiltype, soilunit],
            parameternames=['projectsite', 'soiltype', 'soilunit']
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/soilunit/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            record_id = False
        elif df.__len__() == 1:
            record_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one soil unit was returned, refine search criteria")

        return record_id

    def get_soilunits(self, projectsite=None, soiltype=None, soilunit=None, **kwargs):
        """
        Find all soil units corresponding to the search parameters
        
        :param projectsite: Name of the projectsite (e.g. ``"HKN"``)
        :param soiltype: Name of the soil type (e.g. ``"SAND"``)
        :param soilunit: Name of the soil unit (e.g. ``"Asse sand-clay"``)
        
        :return: Dictionary with the following keys:
        
            - 'data': Dataframe with the soil units returned from the query
            - 'exists': Boolean containing whether data is in the returned query
        """
        url_params = self.urlparameters(
            parameters=[projectsite, soiltype, soilunit],
            parameternames=['projectsite', 'soiltype', 'soilunit']
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/soilunit/' % self.api_root,
            headers=self.header,
            params=url_params)
        try:
            df_summary = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df_summary,
            'exists': exists
        }

    def get_batchlabtests(self, projectsite=None, campaign=None, location=None, testtype=None, batchlabtest=None,
                          **kwargs):
        """
        Retrieve a summary of batch lab tests corresponding to the specified search criteria.

        :param projectsite: Project site name (e.g. 'HKN')
        :param campaign: Title of the survey campaign
        :param location: Title of the test location
        :param testtype: Title of the test type
        :param batchlabtest: Title of the batch lab test
        
        :return: Dictionary with the following keys
        
            - 'data': Dataframe with details on the batch lab test
            - 'exists': Boolean indicating whether records meeting the specified search criteria exist
        """
        url_params = self.urlparameters(
            parameters=[projectsite, campaign, location, testtype, batchlabtest],
            parameternames=['projectsite', 'campaign', 'location', 'testtype', 'batchlabtest']
        )

        url_params = {**url_params, **kwargs}

        resp_summary = requests.get(
            url='%s/batchlabtestsummary/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df_summary = pd.DataFrame(json.loads(resp_summary.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df_summary,
            'exists': exists
        }

    def get_batchlabtesttypes(self, testtype=None, **kwargs):
        """
        Retrieve batch lab test types corresponding to the specified search criteria.

        :param testtype: Title of the test type
        
        :return: Dictionary with the following keys
        
            - 'data': Dataframe with details on the batch lab test types
            - 'exists': Boolean indicating whether records meeting the specified search criteria exist
        """
        url_params = self.urlparameters(
            parameters=[testtype,],
            parameternames=['testtype',]
        )

        url_params = {**url_params, **kwargs}

        resp_summary = requests.get(
            url='%s/batchlabtesttype/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df_summary = pd.DataFrame(json.loads(resp_summary.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df_summary,
            'exists': exists
        }

    def batchlabtesttype_exists(self, batchlabtesttype=None, **kwargs):
        """
        Checks if the batch lab test type answering to the search criteria exists

        :param batchlabtesttype: Title of the sample type

        :return: Returns the id if the batch lab test type exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[batchlabtesttype,],
            parameternames=['testtype',]
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/batchlabtesttype/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            record_id = False
        elif df.__len__() == 1:
            record_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one batch lab test type was returned, refine search criteria")

        return record_id

    def get_proximity_batchlabtests(self, latitude, longitude, radius, **kwargs):
        """
        Get all batch lab tests in a certain radius surrounding a point with given lat/lon
        
        :param latitude: Latitude of the central point in decimal format
        :param longitude: Longitude of the central point in decimal format
        :param radius: Radius around the central point in km
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the batch lab test summary data for each batch lab test in the specified search area
            - 'exists': Boolean indicating whether matching records are found
        """
        return self.get_proximity_entities_2d(
            api_url='batchlabtestproximity',
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            **kwargs)

    def get_closest_batchlabtest(self, latitude, longitude, initialradius=1, target_srid='25831', **kwargs):
        """
        Get the batch lab test closest to a certain point with the name containing a certain string
        
        :param latitude: Latitude of the central point in decimal format
        :param longitude: Longitude of the central point in decimal format
        :param initialradius: Initial search radius around the central point in km, the search radius is increased until locations are found
        :param target_srid: SRID for the offset calculation in meters
        :param kwargs: Optional keyword arguments e.g. ``location__title__icontains='BH'``
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the batch lab test data for each batch lab test in the specified search area
            - 'id': ID of the closest batch lab test
            - 'title': Title of the closest batch lab test
            - 'offset [m]': Offset in meters from the specified point
        """
        return self.get_closest_entity_2d(
            api_url='batchlabtestproximity',
            latitude=latitude,
            longitude=longitude,
            initialradius=initialradius,
            target_srid=target_srid,
            **kwargs
        )

    def get_batchlabtest_detail(self, projectsite=None, location=None, testtype=None, campaign=None,
                                batchlabtest=None, **kwargs):
        """
        Retrieve detailed data for a specific batch lab test

        :param projectsite: Title of the project site
        :param campaign: Title of the survey campaign
        :param location: Title of the test location
        :param testtype: Title of the test type
        :param batchlabtest: Title of the batch lab test
        
        :return: Dictionary with the following keys:
        
            - 'id': id for the selected soil profile
            - 'summary': Metadata for the batch lab test
            - 'response': Response text
            - 'rawdata': Dataframe with the raw data
            - 'processeddata': Dataframe with the raw data
            - 'conditions': Dataframe with test conditions
            - 'exists': Boolean indicating whether a matching record is found
        """
        url_params = self.urlparameters(
            parameters=[projectsite, campaign, location, testtype, batchlabtest],
            parameternames=['projectsite', 'campaign', 'location', 'testtype', 'batchlabtest']
        )

        url_params = {**url_params, **kwargs}

        resp_summary = requests.get(
            url='%s/batchlabtestsummary/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df_summary = pd.DataFrame(json.loads(resp_summary.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
            id = None
        elif df_summary.__len__() == 1:
            exists = True
        else:
            raise ValueError("More than one batch lab test was returned, refine your search parameters.")

        resp_detail = requests.get(
            url='%s/batchlabtestdetail/' % self.api_root,
            headers=self.header,
            params=url_params)
        
        try:
            df_resp_detail = pd.DataFrame(json.loads(resp_detail.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_resp_detail = pd.DataFrame()

        id = df_resp_detail['id'].iloc[0]

        try:
            df_raw = pd.DataFrame(df_resp_detail['rawdata'].iloc[0]).reset_index(drop=True)
        except Exception as err:
            warnings.warn("Raw data could not be loaded. This is most likely because no data was returned")
            df_raw = pd.DataFrame()
        try:
            df_processed = pd.DataFrame(df_resp_detail['processeddata'].iloc[0]).reset_index(drop=True)
        except:
            warnings.warn("Processed data could not be loaded. This is most likely because no data was returned")
            df_processed = pd.DataFrame()
        try:
            df_conditions = pd.DataFrame(df_resp_detail['conditions'].iloc[0]).reset_index(drop=True)
        except:
            warnings.warn("Test conditions could not be loaded. This is most likely because no data was returned")
            df_conditions = pd.DataFrame()

        for _df in [df_raw, df_processed, df_conditions]:
            for col in _df.columns:
                try:
                    _df[col] = pd.to_numeric(_df[col], errors='ignore')
                except:
                    pass

        return {
            'id': id,
            'summary': df_summary,
            'rawdata': df_raw,
            'processed': df_processed,
            'conditions': df_conditions,
            'response': resp_detail,
            'exists': exists
        }

    def batchlabtest_exists(self, projectsite=None, location=None, testtype=None, campaign=None,
                            batchlabtest=None, **kwargs):
        """
        Checks if the batch lab test answering to the search criteria exists

        :param projectsite: Project site name (e.g. 'HKN')
        :param campaign: Title of the survey campaign
        :param location: Title of the test location
        :param testtype: Title of the test type
        :param batchlabtest: Title of the batch lab test

        :return: Returns the id if batch lab test exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[projectsite, campaign, location, testtype, batchlabtest],
            parameternames=['projectsite', 'campaign', 'location', 'testtype', 'batchlabtest']
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/batchlabtestdetail/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            record_id = False
        elif df.__len__() == 1:
            record_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one batch lab test was returned, refine search criteria")

        return record_id

    def get_geotechnicalsampletypes(self, sampletype=None, **kwargs):
        """
        Retrieve geotechnical sample types corresponding to the specified search criteria

        :param sampletype: Title of the sample type
        
        :return: Dictionary with the following keys
        
            - 'data': Dataframe with details on the sample type
            - 'exists': Boolean indicating whether records meeting the specified search criteria exist
        """
        url_params = self.urlparameters(
            parameters=[sampletype,],
            parameternames=['sampletype',]
        )

        url_params = {**url_params, **kwargs}

        resp_summary = requests.get(
            url='%s/geotechnicalsampletype/' % self.api_root,
            headers=self.header,
            params=url_params)
        
        try:
            df_summary = pd.DataFrame(json.loads(resp_summary.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df_summary,
            'exists': exists
        }

    def geotechnicalsampletype_exists(self, sampletype=None, **kwargs):
        """
        Checks if the geotechnical sample type answering to the search criteria exists

        :param sampletype: Title of the sample type

        :return: Returns the id if the sample type exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[sampletype,],
            parameternames=['sampletype',]
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/geotechnicalsampletype/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            record_id = False
        elif df.__len__() == 1:
            record_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one sample type was returned, refine search criteria")

        return record_id

    def get_geotechnicalsamples(self, projectsite=None, campaign=None, location=None, sampletype=None, sample=None,
                                **kwargs):
        """
        Retrieve geotechnical samples corresponding to the specified search criteria
        
        :param projectsite: Project site name (e.g. 'HKN')
        :param campaign: Title of the survey campaign
        :param location: Title of the test location
        :param sampletype: Title of the sample type
        :param sample: Title of the sample
        
        :return: Dictionary with the following keys
        
            - 'data': Dataframe with details on the sample
            - 'exists': Boolean indicating whether records meeting the specified search criteria exist
        """
        url_params = self.urlparameters(
            parameters=[projectsite, campaign, location, sampletype, sample],
            parameternames=['projectsite', 'campaign', 'location', 'sampletype', 'sample']
        )

        url_params = {**url_params, **kwargs}

        resp_summary = requests.get(
            url='%s/geotechnicalsample/' % self.api_root,
            headers=self.header,
            params=url_params)
        
        try:
            df_summary = pd.DataFrame(json.loads(resp_summary.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df_summary,
            'exists': exists
        }

    def get_proximity_geotechnicalsamples(self, latitude, longitude, radius, **kwargs):
        """
        Get all geotechnical samples in a certain radius surrounding a point with given lat/lon
        
        :param latitude: Latitude of the central point in decimal format
        :param longitude: Longitude of the central point in decimal format
        :param radius: Radius around the central point in km
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the geotechnical sample data for each geotechnical sample in the specified search area
            - 'exists': Boolean indicating whether matching records are found
        """
        return self.get_proximity_entities_2d(
            api_url='geotechnicalsampleproximity',
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            **kwargs)

    def get_closest_geotechnicalsample(self, latitude, longitude, depth, initialradius=1, target_srid='25831', **kwargs):
        """
        Get the geotechnical sample closest to a certain point with the name containing a certain string
        
        :param latitude: Latitude of the central point in decimal format
        :param longitude: Longitude of the central point in decimal format
        :param depth: Depth of the central point in meters below seabed
        :param initialradius: Initial search radius around the central point in km, the search radius is increased until locations are found
        :param target_srid: SRID for the offset calculation in meters
        :param kwargs: Optional keyword arguments e.g. ``location__title__icontains='BH'``
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the geotechnical sample data for each geotechnical sample in the specified search area
            - 'id': ID of the closest batch lab test
            - 'title': Title of the closest batch lab test
            - 'offset [m]': Offset in meters from the specified point
        """
        return self.get_closest_entity_3d(
            api_url='geotechnicalsampleproximity',
            latitude=latitude,
            longitude=longitude,
            depth=depth,
            initialradius=initialradius,
            target_srid=target_srid,
            sampletest=False,
            **kwargs
        )

    def get_geotechnicalsample_detail(self, projectsite=None, location=None, sampletype=None, campaign=None,
                                      sample=None, **kwargs):
        """
        Retrieve detailed data for a specific sample.

        :param projectsite: Title of the project site
        :param campaign: Title of the survey campaign
        :param location: Title of the test location
        :param sampletype: Title of the sample type
        :param sample: Title of the sample
        
        :return: Dictionary with the following keys:
        
            - 'id': id for the selected soil profile
            - 'data': Metadata for the batch lab test
            - 'response': Response text
            - 'exists': Boolean indicating whether a matching record is found
        """
        url_params = self.urlparameters(
            parameters=[projectsite, campaign, location, sampletype, sample],
            parameternames=['projectsite', 'campaign', 'location', 'sampletype', 'sample']
        )

        url_params = {**url_params, **kwargs}

        resp_summary = requests.get(
            url='%s/geotechnicalsample/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df_summary = pd.DataFrame(json.loads(resp_summary.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
            id = None
        elif df_summary.__len__() == 1:
            exists = True
            id = df_summary['id'].iloc[0]
        else:
            raise ValueError("More than one sample was returned, refine your search parameters.")

        return {
            'id': id,
            'data': df_summary,
            'response': resp_summary,
            'exists': exists
        }

    def geotechnicalsample_exists(self, projectsite=None, location=None, sampletype=None, campaign=None, sample=None,
                                  **kwargs):
        """
        Checks if the geotechnical sample answering to the search criteria exists

        :param projectsite: Project site name (e.g. 'HKN')
        :param campaign: Title of the survey campaign
        :param location: Title of the test location
        :param sampletype: Title of the sample type
        :param sample: Title of the sample

        :return: Returns the id if the geotechnical sample exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[projectsite, campaign, location, sampletype, sample],
            parameternames=['projectsite', 'campaign', 'location', 'sampletype', 'sample']
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/geotechnicalsample/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            record_id = False
        elif df.__len__() == 1:
            record_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one geotechnical sample was returned, refine search criteria")

        return record_id

    def get_sampletesttypes(self, testtype=None, **kwargs):
        """
        Retrieve a summary of geotechnical sample lab tests types corresponding to the specified search criteria

        :param testtype: Title of the test type
        
        :return: Dictionary with the following keys
        
            - 'data': Dataframe with details on the sample lab test types
            - 'exists': Boolean indicating whether records meeting the specified search criteria exist
        """
        url_params = self.urlparameters(
            parameters=[testtype,],
            parameternames=['testtype',]
        )

        url_params = {**url_params, **kwargs}

        resp_summary = requests.get(
            url='%s/sampletesttype/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df_summary = pd.DataFrame(json.loads(resp_summary.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df_summary,
            'exists': exists
        }

    def get_sampletests(self, projectsite=None, campaign=None, location=None, sample=None, testtype=None,
                        sampletest=None, **kwargs):
        """
        Retrieve a summary of geotechnical sample lab tests corresponding to the specified search criteria

        :param projectsite: Title of the project site
        :param campaign: Title of the survey campaign
        :param location: Title of the test location
        :param sample: Title of the sample
        :param testtype: Title of the test type
        :param sampletest: Title of the sample test

        :return: Dictionary with the following keys
        
            - 'data': Dataframe with details on the lab test
            - 'exists': Boolean indicating whether records meeting the specified search criteria exist
        """
        url_params = self.urlparameters(
            parameters=[projectsite, campaign, location, sample, testtype, sampletest],
            parameternames=['projectsite', 'campaign', 'location', 'sample', 'testtype', 'sampletest']
        )

        url_params = {**url_params, **kwargs}

        resp_summary = requests.get(
            url='%s/sampletestsummary/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df_summary = pd.DataFrame(json.loads(resp_summary.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df_summary,
            'exists': exists
        }

    def get_proximity_sampletests(self, latitude, longitude, radius, **kwargs):
        """
        Get all sample tests in a certain radius surrounding a point with given lat/lon
        
        :param latitude: Latitude of the central point in decimal format
        :param longitude: Longitude of the central point in decimal format
        :param radius: Radius around the central point in km
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the sample test summary data for each sample test in the specified search area
            - 'exists': Boolean indicating whether matching records are found
        """
        return self.get_proximity_entities_2d(
            api_url='sampletestproximity',
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            **kwargs)

    def get_closest_sampletest(self, latitude, longitude, depth, initialradius=1, target_srid='25831', **kwargs):
        """
        Get the sample test closest to a certain point
        
        :param latitude: Latitude of the central point in decimal format
        :param longitude: Longitude of the central point in decimal format
        :param Depth: Depth of the central point in meters below seabed
        :param initialradius: Initial search radius around the central point in km, the search radius is increased until locations are found
        :param target_srid: SRID for the offset calculation in meters
        :param kwargs: Optional keyword arguments e.g. ``sample__location__title__icontains='BH'``
        
        :return: Dictionary with the following keys:
        
            - 'data': Pandas dataframe with the sample test data for each sample test in the specified search area
            - 'id': ID of the closest sample test
            - 'title': Title of the closest sample test
            - 'offset [m]': Offset in meters from the specified point
        """
        return self.get_closest_entity_3d(
            api_url='sampletestproximity',
            latitude=latitude,
            longitude=longitude,
            depth=depth,
            initialradius=initialradius,
            target_srid=target_srid,
            **kwargs
        )

    def sampletesttype_exists(self, sampletesttype=None, **kwargs):
        """
        Checks if the sample test type answering to the search criteria exists

        :param sampletesttype: Title of the sample test type

        :return: Returns the id if the sample test type exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[sampletesttype,],
            parameternames=['testtype',]
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/sampletesttype/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            record_id = False
        elif df.__len__() == 1:
            record_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one sample test type was returned, refine search criteria")

        return record_id

    def get_sampletest_detail(self, projectsite=None, location=None, testtype=None, sample=None, campaign=None,
                              sampletest=None, **kwargs):
        """
        Retrieves detailed information on a specific sample test based on the specified search criteria

        :param projectsite: Title of the project site
        :param campaign: Title of the survey campaign
        :param location: Title of the test location
        :param sample: Title of the sample
        :param testtype: Title of the test type
        :param sampletest: Title of the sample test

        :return: Dictionary with the following keys:
        
            - 'id': id for the selected lab test
            - 'summary': Metadata for the lab test
            - 'response': Response text
            - 'rawdata': Dataframe with the raw data
            - 'processeddata': Dataframe with the raw data
            - 'conditions': Dataframe with test conditions
            - 'exists': Boolean indicating whether a matching record is found
        """
        url_params = self.urlparameters(
            parameters=[projectsite, campaign, location, sample, testtype, sampletest],
            parameternames=['projectsite', 'campaign', 'location', 'sample', 'testtype', 'sampletest']
        )

        url_params = {**url_params, **kwargs}

        resp_summary = requests.get(
            url='%s/sampletestsummary/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df_summary = pd.DataFrame(json.loads(resp_summary.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_summary = pd.DataFrame()

        if df_summary.__len__() == 0:
            exists = False
            sample_test_id = None
        elif df_summary.__len__() == 1:
            exists = True
        else:
            raise ValueError("More than one sample lab test was returned, refine your search parameters.")

        resp_detail = requests.get(
            url='%s/sampletestdetail/' % self.api_root,
            headers=self.header,
            params=url_params)
        
        try:
            df_resp_detail = pd.DataFrame(json.loads(resp_detail.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df_resp_detail = pd.DataFrame()

        try:
            sample_test_id = df_resp_detail['id'].iloc[0]
        except:
            sample_test_id = None

        try:
            df_raw = pd.DataFrame(df_resp_detail['rawdata'].iloc[0]).reset_index(drop=True)
        except Exception as err:
            try:
                df_raw = pd.DataFrame([df_resp_detail['rawdata'].iloc[0]]).reset_index(drop=True)
            except:
                warnings.warn("Raw data could not be loaded. This is most likely because no data was returned")
                df_raw = pd.DataFrame()
        try:
            df_processed = pd.DataFrame(df_resp_detail['processeddata'].iloc[0]).reset_index(drop=True)
        except:
            warnings.warn("Processed data could not be loaded. This is most likely because no data was returned")
            df_processed = pd.DataFrame()
        try:
            df_conditions = pd.DataFrame(df_resp_detail['conditions'].iloc[0]).reset_index(drop=True)
        except:
            warnings.warn("Test conditions could not be loaded. This is most likely because no data was returned")
            df_conditions = pd.DataFrame()

        for _df in [df_raw, df_processed, df_conditions]:
            for col in _df.columns:
                try:
                    _df[col] = pd.to_numeric(_df[col], errors='ignore')
                except:
                    pass

        return {
            'id': sample_test_id,
            'summary': df_summary,
            'rawdata': df_raw,
            'processed': df_processed,
            'conditions': df_conditions,
            'response': resp_detail,
            'exists': exists
        }

    def sampletest_exists(self, projectsite=None, location=None, testtype=None, sample=None, campaign=None,
                          sampletest=None, **kwargs):
        """
        Checks if the laboratory test answering to the search criteria exists

        :param projectsite: Title of the project site
        :param campaign: Title of the survey campaign
        :param location: Title of the test location
        :param sample: Title of the sample
        :param testtype: Title of the test type
        :param sampletest: Title of the sample test

        :return: Returns the id if the laboratory test exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[projectsite, campaign, location, sample, testtype, sampletest],
            parameternames=['projectsite', 'campaign', 'location', 'sample', 'testtype', 'sampletest']
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/sampletestdetail/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        if df.__len__() == 0:
            record_id = False
        elif df.__len__() == 1:
            record_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one sample test was returned, refine search criteria")

        return record_id

    def get_soilunit_depthranges(self, soilunit, projectsite=None, location=None, **kwargs):
        """
        Retrieves the depth ranges for where the soil unit occurs

        :param soilunit: Title of the soil unit for which depth ranges need to be retrieved
        :param projectsite: Title of the project site (optional)
        :param location: Title of the test location (optional)

        :return: Returns the id if the sample test exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[soilunit, projectsite, location],
            parameternames=['soilunit', 'projectsite', 'location']
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/soillayer/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            df = pd.DataFrame()

        return df

    def get_unit_insitutestdata(self, soilunit, depthcol="z [m]", **kwargs):
        """
        Retrieves proportions of in-situ test data located inside a soil unit.
        The data in the ``rawdata`` field is filtered based on the depth column.

        :param soilunit: Name of the soil unit
        :param depthcol: Name of the column with the depth in the ``rawdata`` field
        :param kwargs: Optional keyword arguments for retrieval of in-situ tests (e.g. ``projectsite`` and ``testtype``)
        
        :return: Dataframe with in-situ test data in the selected soil unit.
        """

        selected_depths = self.get_soilunit_depthranges(soilunit=soilunit)
        selected_tests = self.get_insitutests(**kwargs)['data']
        all_unit_data = pd.DataFrame()
        for i, row in selected_tests.iterrows():
            unitdata = pd.DataFrame()

            if row['location_name'] in selected_depths['location_name'].unique():
                _fulldata = self.get_insitutest_detail(
                    location=row['location_name'], **kwargs)['rawdata']
                _depthranges = selected_depths[selected_depths['location_name'] == row['location_name']]
                for j, _layer in _depthranges.iterrows():
                    _unitdata = _fulldata[(_fulldata[depthcol] >= _layer['start_depth']) &
                                          (_fulldata[depthcol] <= _layer['end_depth'])]
                    unitdata = pd.concat([unitdata,_unitdata])
                unitdata.reset_index(drop=True, inplace=True)
                unitdata.loc[:, "location_name"] = row['location_name']
                unitdata.loc[:, "projectsite_name"] = row['projectsite_name']
                unitdata.loc[:, "test_type_name"] = row['test_type_name']
            else:
                pass
            all_unit_data = pd.concat([all_unit_data, unitdata])

        all_unit_data.reset_index(drop=True, inplace=True)

        return all_unit_data

    def get_unit_batchlabtestdata(self, soilunit, depthcol="z [m]", **kwargs):
        """
        Retrieves proportions of batch lab test data located inside a soil unit.
        The data in the ``rawdata`` field is filtered based on the depth column.

        :param soilunit: Name of the soil unit
        :param depthcol: Name of the column with the depth in the ``rawdata`` field
        :param kwargs: Optional keyword arguments for retrieval of in-situ tests (e.g. ``projectsite`` and ``testtype``)
        :return: Dataframe with batch lab test data in the selected soil unit.
        """

        selected_depths = self.get_soilunit_depthranges(soilunit=soilunit)
        selected_tests = self.get_batchlabtests(**kwargs)['data']

        all_unit_data = pd.DataFrame()
        for i, row in selected_tests.iterrows():
            unitdata = pd.DataFrame()

            if row['location_name'] in selected_depths['location_name'].unique():
                _fulldata = self.get_batchlabtest_detail(
                    location=row['location_name'], **kwargs)['rawdata']
                _depthranges = selected_depths[selected_depths['location_name'] == row['location_name']]
                for j, _layer in _depthranges.iterrows():
                    _unitdata = _fulldata[(_fulldata[depthcol] >= _layer['start_depth']) &
                                          (_fulldata[depthcol] <= _layer['end_depth'])]
                    unitdata = pd.concat([unitdata,_unitdata])
                unitdata.reset_index(drop=True, inplace=True)
                unitdata.loc[:, "location_name"] = row['location_name']
                unitdata.loc[:, "projectsite_name"] = row['projectsite_name']
                unitdata.loc[:, "test_type_name"] = row['test_type_name']
            else:
                print("Soil unit not found for %s" % row['location_name'])
            all_unit_data = pd.concat([all_unit_data, unitdata])

        all_unit_data.reset_index(drop=True, inplace=True)

        return all_unit_data

    def get_unit_sampletests(self, soilunit, **kwargs):
        """
        Retrieves the sample tests data located inside a soil unit.
        The metadata of the samples is filtered based on the depth column.
        Further retrieval of the test data can follow after this method.

        :param soilunit: Name of the soil unit
        :param kwargs: Optional keyword arguments for retrieval of sample tests (e.g. ``projectsite`` and ``testtype``)
        
        :return: Dataframe with sample test metadata in the selected soil unit.
        """
        selected_depths = self.get_soilunit_depthranges(soilunit=soilunit)
        selected_tests = self.get_sampletests(**kwargs)['data']

        all_unit_data = pd.DataFrame()
        for i, row in selected_tests.iterrows():
            unitdata = pd.DataFrame()

            if row['location_name'] in selected_depths['location_name'].unique():

                _depthranges = selected_depths[selected_depths['location_name'] == row['location_name']]
                for j, _layer in _depthranges.iterrows():
                    if row['depth'] >= _layer['start_depth'] and row['depth'] <= _layer['end_depth']:
                        _unitdata = selected_tests[selected_tests['id'] == row['id']]
                        unitdata = pd.concat([unitdata,_unitdata])
                    else:
                        pass

                unitdata.reset_index(drop=True, inplace=True)
            else:
                pass
            all_unit_data = pd.concat([all_unit_data, unitdata])

        all_unit_data.reset_index(drop=True, inplace=True)
        return all_unit_data

    def get_soilprofile_profile(self, lat1, lon1, lat2, lon2, band=1000):
        """
        Retrieves soil profiles along a profile line
        
        :param lat1: Latitude of the start point
        :param lon1: Longitude of the start point
        :param lat2: Latitude of the end point
        :param lon2: Longitude of the end point
        :param band: Thickness of the band (in m, default=1000m)
        
        :return: Returns a dataframe with the summary data of the selected soil profiles
        """
        resp = requests.get(
            url='%s/soilprofileprofile/' % self.api_root,
            headers=self.header,
            params={
                'lat1': lat1,
                'lon1': lon1,
                'lat2': lat2,
                'lon2': lon2,
                'offset': band
            })

        try:
            return pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            return pd.DataFrame()



    def plot_soilprofile_fence(self, soilprofiles_df, start, end,
                               fillcolordict={'SAND': 'yellow', 'CLAY': 'brown', 'SAND/CLAY': 'orange'},
                               logwidth=100, show_annotations=True,
                               general_layout=dict(),
                               **kwargs):
        """
        Creates a fence diagram for soil profiles
        
        :param soilprofiles_df: Dataframe with summary data for the selected soil profiles
        :param start: Name of the soil profile at the start
        :param end: Name of the soil profile at the end
        :param fillcolordict: Dictionary used for mapping soil types to colors
        :param logwidth: Width of the logs in the fence diagram (default=100)
        :param show_annotations: Boolean determining whether annotations are shown (default=True)
        :param general_layout: Dictionary with general layout options (default = dict())
        :param kwargs: Keyword arguments for the get_soilprofiles method
        
        :return: Plots a fence diagram of the selected soil profiles
        """

        selected_profiles = soilprofiles_df

        soilprofiles = []

        for i, row in selected_profiles.iterrows():
            _profile = self.get_soilprofile_detail(
                projectsite=row['projectsite_name'], location=row['location_name'], soilprofile=row['title'],
                drop_info_cols=False, profile_title=row['location_name'])['soilprofile']
            _profile.set_position(easting=row['easting'], northing=row['northing'], elevation=row['elevation'])
            soilprofiles.append(_profile)

        fence_diagram_1 = plot_fence_diagram(
            profiles=soilprofiles,
            start=start,
            end=end,
            latlon=True,
            fillcolordict=fillcolordict,
            logwidth=logwidth,
            show_annotations=show_annotations,
            general_layout=general_layout
        )

        return {
            'profiles': soilprofiles,
            'diagram': fence_diagram_1
        }

    def get_insitutests_profile(self, lat1, lon1, lat2, lon2, band=1000):
        """
        Retrieves in-situ tests along a profile line
        
        :param lat1: Latitude of the start point
        :param lon1: Longitude of the start point
        :param lat2: Latitude of the end point
        :param lon2: Longitude of the end point
        :param band: Thickness of the band (in m, default=1000m)
        
        :return: Returns a dataframe with the summary data of the selected in-situ tests
        """
        resp = requests.get(
            url='%s/insitutestprofile/' % self.api_root,
            headers=self.header,
            params={
                'lat1': lat1,
                'lon1': lon1,
                'lat2': lat2,
                'lon2': lon2,
                'offset': band
            })
        try:
            return pd.DataFrame(json.loads(resp.text))
        except:
            warnings.warn("Response could not be loaded. This is most likely because no data was returned")
            return pd.DataFrame()

    def plot_cpt_fence(self, cpt_df, start, end, band=1000,
                       scale_factor=10, extend_profile=True,
                       show_annotations=True,
                       general_layout=dict(),
                       uniformcolor=None, **kwargs):
        """
        Creates a fence diagram for CPTs
        
        :param cpt_df: Dataframe with the summary data of the selected CPTs
        :param start: Name of the location for the start point
        :param end: Name of the location for the end point
        :param band: Thickness of the band (in m, default=1000m)
        :param scale_factor: Width of the CPT axis in the fence diagram (default=10)
        :param extend_profile: Boolean determining whether the profile needs to be extended (default=True)
        :param show_annotations: Boolean determining whether annotations are shown (default=True)
        :param general_layout: Dictionary with general layout options (default = dict())
        :param uniformcolor: If a valid color is provided (e.g. 'black'), it is used for all CPT traces
        :param kwargs: Keyword arguments for the get_insitutests method
        
        :return: Plots a fence diagram of the selected CPT tests
        """

        selected_cpts = cpt_df

        cpts = []

        for i, row in selected_cpts.iterrows():
            try:
                _cpt = self.get_cpttest_detail(
                    projectsite=row['projectsite_name'], location=row['location_name'],
                    insitutest=row['title'], testtype=row['test_type_name'])['cpt']
                _cpt.set_position(easting=row['easting'], northing=row['northing'], elevation=row['elevation'])
                cpts.append(_cpt)
            except Exception as err:
                print("%s for %s" % (str(err), str(row['title'])))

        cpt_fence_fig_1 = plot_longitudinal_profile(
            cpts=cpts,
            latlon=True,
            start=start,
            end=end,
            band=band,
            scale_factor=scale_factor,
            extend_profile=extend_profile,
            show_annotations=show_annotations,
            general_layout=general_layout,
            uniformcolor=uniformcolor
        )

        return {
            'cpts': cpts,
            'diagram': cpt_fence_fig_1
        }

    def plot_combined_fence(self, profiles, cpts, startpoint, endpoint, band=1000,
                       scale_factor=10, extend_profile=True,
                       show_annotations=True,
                       general_layout=dict(),
                       fillcolordict={'SAND': 'yellow', 'CLAY': 'brown', 'SAND/CLAY': 'orange'},
                       logwidth=100, opacity=0.5,
                       uniformcolor=None, **kwargs):
        """
        Creates a combined fence diagram with soil profile and CPT data:
        
        :param profiles: List with georeferenced soil profiles (run plot_soilprofile_fence first)
        :param cpts: List with georeference CPTs (run plot_cpt_fence first)
        :param startpoint: Name of the CPT location for the start point
        :param endpoint: Name of the CPT location for the end point
        :param band: Thickness of the band (in m, default=1000m)
        :param scale_factor: Width of the CPT axis in the fence diagram (default=10)
        :param extend_profile: Boolean determining whether the profile needs to be extended (default=True)
        :param show_annotations: Boolean determining whether annotations are shown (default=True)
        :param general_layout: Dictionary with general layout options (default = dict())
        :param fillcolordict: Dictionary with colors for soil types
        :param logwidth: Width of the log in the fence diagram
        :param uniformcolor: If a valid color is provided (e.g. 'black'), it is used for all CPT traces
        
        :return: Plots a fence diagram of the selected CPT tests and soil profiles
        """

        combined_fence_fig_1 = plot_combined_longitudinal_profile(
            cpts=cpts,
            profiles=profiles,
            latlon=True,
            start=startpoint,
            end=endpoint,
            band=band,
            scale_factor=scale_factor,
            logwidth=logwidth,
            opacity=opacity,
            extend_profile=extend_profile,
            show_annotations=show_annotations,
            uniformcolor=uniformcolor,
            fillcolordict=fillcolordict,
            general_layout=general_layout)

        return {
            'diagram': combined_fence_fig_1
        }

    # Region upload - Write permissions required

    def upload_location(self, location_api, projectsite, surveycampaign, location, longitude, latitude, elevation,
        description="", additional_data={}, user_id=1):
        """
        Uploads test location data based on the provided details. If the location already exists, it is updated.

        :param location_api: Instance of a LocationsAPI object used for connecting to the models of the location app
        :param projectsite: Title of the project site
        :param surveycampaign: Title of the survey campaign
        :param location: Title of the location
        :param longitude: Longitude of the location position
        :param latitude: Latitude of the location position
        :param elevation: Elevation of the location position
        :param description: Optional description of the location
        :param additional_data: Optional JSON field with additional data
        :param user_id: ID of the user performing the upload

        :return: Returns the response after POST or PUT request
        """
        project_id = location_api.projectsite_exists(projectsite)

        if not project_id:
            raise IOError("Specified project site does not exist")

        campaign_id = self.surveycampaign_exists(projectsite=projectsite, campaign=surveycampaign)

        if not campaign_id:
            raise IOError("Specified survey campaign does not exist")

        data = {
            "title": location,
            "description": description,
            "position": 'SRID=4326;POINT (%.10f %.10f)' % (longitude, latitude),
            "elevation": elevation,
            "active": True,
            "additional_data": additional_data,
            "created_by": user_id,
            "modified_by": user_id,
            "projectsite": project_id,
            "campaign": campaign_id
        }

        location_id = self.testlocation_exists(projectsite=projectsite, campaign=surveycampaign, location=location)

        if not location_id:
            print("Location %s does not exist, creating" % location)
            resp = requests.post(
                '%s/routes/testlocation/' % SOIL_URL_PREFIX,
                headers=self.header,
                data=data)
        else:
            print("Location %s already exists, updating" % location)
            resp = requests.put(
                '%s/routes/testlocation/%i/' % (
                    SOIL_URL_PREFIX,
                    location_id),
                headers=self.header,
                data=data)

        return resp

    def upload_insitutest_data(self, projectsite, surveycampaign, location, testtype, test_title,
        start_depth, end_depth, rawdata, processeddata=None, conditions=None, description="", additional_data={}, user_id=1,
        test_date="2020-01-01"):
        """
        Uploads in-situ test data to the database

        :param projectsite: Title of the project site
        :param surveycampaign: Title of the survey campaign
        :param location: Title of the location
        :param testtype: Title of the in-situ test type
        :param test_title: Title of the in-situ test
        :param start_depth: Depth where the test was started
        :param end_depth: Depth where the test was ended
        :param rawdata: Valid JSON with raw data
        :param processeddata: Optional valid JSON with processed data
        :param conditions: Optional valid JSON with test conditions
        :param description: Optional description of the test
        :param additional_data: Valid JSON with additional data
        :param user_id: ID of the user performing the upload
        :param test_data: Optional: Date when the test was performed

        :return: Returns the response after POST or PUT request
        """
        location_id = self.testlocation_exists(
            projectsite=projectsite, campaign=surveycampaign, location=location)

        if not location_id:
            raise IOError("Specified test location does not exist")

        testtype_id = self.insitutesttype_exists(testtype=testtype)

        if not testtype_id:
            raise IOError("Specified test type does not exist")
        
        # Prepare the data
        data = {
            "title": test_title,
            "description": description,
            "start_depth": start_depth,
            "end_depth": end_depth,
            "rawdata": rawdata,
            "created_by": user_id, # pk of the user creating the object
            "modified_by": user_id, # pk of the user modifying the object
            "test_type": testtype_id, # pk of the project site
            "location": location_id, # pk of the test location
            "test_date": test_date,
            "additional_data": additional_data
        }

        if processeddata is not None:
            data["processeddata"] = processeddata
        if conditions is not None:
            data["conditions"] = conditions
        
        # Check if the in-situ test already exists
        test_id = self.insitutest_exists(
            projectsite=projectsite, campaign=surveycampaign,
            location=location, testtype=testtype, insitutest=test_title)
        
        if not test_id:
            print("In-situ test %s does not exist, creating" % test_title)
            resp = requests.post(
                '%s/routes/insitutest/' % SOIL_URL_PREFIX,
                headers=self.header,
                data=data)
        else:
            print("In-situ test %s already exists, updating" % test_title)
            resp = requests.put(
                '%s/routes/insitutest/%i/' % (
                    SOIL_URL_PREFIX,
                    test_id),
                headers=self.header,
                data=data)

        return resp

    def upload_batchlabtest_data(self, projectsite, surveycampaign, location, testtype, test_title,
        start_depth, end_depth, rawdata, processeddata=None, conditions=None, description="", additional_data={}, user_id=1,
        test_date="2020-01-01"):
        """
        Uploads a batch lab test to the database.

        :param projectsite: Title of the project site
        :param surveycampaign: Title of the survey campaign
        :param location: Title of the location
        :param testtype: Title of the batch lab test type
        :param test_title: Title of the batch lab test
        :param start_depth: Depth where the test was started
        :param end_depth: Depth where the test was ended
        :param rawdata: Valid JSON with raw data
        :param processeddata: Optional valid JSON with processed data
        :param conditions: Optional valid JSON with test conditions
        :param description: Optional description of the test
        :param additional_data: Valid JSON with additional data
        :param user_id: ID of the user performing the upload
        :param test_data: Optional: Date when the test was performed

        :return: Returns the response after POST or PUT request
        """
        location_id = self.testlocation_exists(
            projectsite=projectsite, campaign=surveycampaign, location=location)

        if not location_id:
            raise IOError("Specified test location does not exist")

        testtype_id = self.batchlabtesttype_exists(testtype=testtype)

        if not testtype_id:
            raise IOError("Specified test type does not exist")
        
        # Prepare the data
        data = {
            "title": test_title,
            "description": description,
            "start_depth": start_depth,
            "end_depth": end_depth,
            "rawdata": rawdata,
            "created_by": user_id, # pk of the user creating the object
            "modified_by": user_id, # pk of the user modifying the object
            "test_type": testtype_id, # pk of the project site
            "location": location_id, # pk of the test location
            "test_date": test_date,
            "additional_data": additional_data
        }

        if processeddata is not None:
            data["processeddata"] = processeddata
        if conditions is not None:
            data["conditions"] = conditions
        
        # Check if the batch lab test already exists
        test_id = self.batchlabtest_exists(
            projectsite=projectsite, campaign=surveycampaign,
            location=location, testtype=testtype, insitutest=test_title)
        
        if not test_id:
            print("Batch lab test %s does not exist, creating" % test_title)
            resp = requests.post(
                '%s/routes/batchlabtest/' % SOIL_URL_PREFIX,
                headers=self.header,
                data=data)
        else:
            print("Batch lab test %s already exists, updating" % test_title)
            resp = requests.put(
                '%s/routes/batchlabtest/%i/' % (
                    SOIL_URL_PREFIX,
                    test_id),
                headers=self.header,
                data=data)

        return resp

    def upload_geotechnicalsample_data(self, projectsite, location, sampletype, sample_title, top_depth, bottom_depth,
        additional_data={}, description="", user_id=1):
        """
        Uploads a geotechnical sample to the database

        :param projectsite: Title of the project site
        :param location: Title of the location
        :param sampletype: Title of the sample type
        :param sample_title: Title of the sample
        :param top_depth: Depth of the top of the sample
        :param bottom_depth: Depth of the bottom of the sample
        :param description: Optional description of the test
        :param additional_data: Valid JSON with additional data
        :param user_id: ID of the user performing the upload
        
        :return: Returns the response after POST or PUT request
        """
        location_id = self.testlocation_exists(projectsite=projectsite, location=location)

        if not location_id:
            raise IOError("Specified test location does not exist")

        sampletype_id = self.geotechnicalsampletype_exists(sampletype=sampletype)
    
        if not sampletype_id:
            raise IOError("Specified sample type does not exist")

        _data = {
            'title': sample_title,
            'description': description,
            'sample_type': sampletype_id,
            'location': location_id,
            'top_depth': top_depth,
            'bottom_depth': bottom_depth,
            "created_by": user_id, # pk of the user creating the object
            "modified_by": user_id,
            "additional_data": additional_data
        }
        
        sample_id = self.geotechnicalsample_exists(
            projectsite=projectsite, location=location, sampletype=sampletype, sample=sample_title)
        
        if not sample_id:
            print("Sample %s does not exist, creating" % sample_title)
            resp = requests.post(
                '%s/routes/geotechnicalsample/' % SOIL_URL_PREFIX,
                headers=self.header,
                data=_data)
        else:
            print("Sample %s already exists, updating" % sample_title)
            resp = requests.put(
                '%s/routes/geotechnicalsample/%i/' % (
                    SOIL_URL_PREFIX,
                    sample_id),
                headers=self.header,
                data=_data)

        return resp

    def upload_sampletest_data(self, projectsite, location, sample, testtype, test_title,
        depth, rawdata, processeddata=None, conditions=None, description="",
        additional_data={}, user_id=1):
        """
        Uploads data for a sampletest to the database

        :param projectsite: Title of the project site
        :param location: Title of the location
        :param sample: Title of the sample
        :param testtype: Title of the lab test type
        :param test_title: Title of the lab test
        :param depth: Depth of the specimen
        :param rawdata: Valid JSON with raw data
        :param processeddata: Optional valid JSON with processed data
        :param conditions: Optional valid JSON with test conditions
        :param description: Optional description of the test
        :param additional_data: Valid JSON with additional data
        :param user_id: ID of the user performing the upload
        
        :return: Returns the response after POST or PUT request
        """
        sample_id = self.geotechnicalsample_exists(
            projectsite=projectsite, location=location,
            sample=sample)

        testtype_id = self.sampletesttype_exists(sampletesttype=testtype)

        if not testtype_id:
            raise IOError("Specified test type does not exist")
        
        if not sample_id:
            print("Sample %s not found, aborting" % sample)
        else:
            sample_test_data = {
                'title': test_title,
                'description': description,
                'sample': sample_id,
                'test_type': testtype_id,
                'depth': depth,
                'rawdata': rawdata,
                "created_by": user_id, # pk of the user creating the object
                "modified_by": user_id,
                "additional_data": additional_data
            }

            if conditions is not None:
                sample_test_data['conditions'] = conditions
            if processeddata is not None:
                sample_test_data['processeddata'] = processeddata
            
            sample_test_id = self.sampletest_exists(
                projectsite=projectsite,
                location=location,
                sample=sample,
                testtype=testtype,
                sampletest=test_title)

            if not sample_test_id:
                print("Sample test %s does not exist, creating" % test_title)
                resp = requests.post(
                    '%s/routes/sampletest/' % SOIL_URL_PREFIX,
                    headers=self.header,
                    data=sample_test_data)
            else:
                print("Sample test %s already exists, updating" % test_title)
                resp = requests.put(
                    '%s/routes/sampletest/%i/' % (
                        SOIL_URL_PREFIX,
                        sample_test_id),
                    headers=self.header,
                    data=sample_test_data)

    def upload_soilprofile(self, location_api, soilprofile, projectsite, location, profile_title,
        description="", water_level=0,
        create_units=False, asset_location=True,
        drop_cols=['Depth from [m]', 'Depth to [m]', 'Soil type', 'Soil unit', 'Total unit weight [kN/m3]'],
        additional_data={}, user_id=1):
        """
        Uploads a soilprofile to the database

        :param location_api: LocationsAPI instance for connection to the locations app
        :param soilprofile: SoilProfile object or Pandas dataframe with the layering and associated parameters
        :param projectsite: Title of the project site
        :param location: Title of the location
        :param profile_title: Title of the lab test
        :param water_level: Optional water level in the borehole (default=0 for water at surface)
        :param create_units: Boolean determining whether soil units which do not exist need to be created (default=False)
        :param asset_location: Boolean determining whether the soil profile needs to be attached to an asset location or test location (default=True)
        :param drop_cols: Columns to drop from the layer (the ones already included in the other fields)
        :param additional_data: Valid JSON with additional data
        :param user_id: ID of the user performing the upload
        
        :return: Returns the response after POST or PUT request
        """
        project_id = location_api.projectsite_exists(projectsite)

        if not project_id:
            raise IOError("Specified project site does not exist")

        if asset_location:
            location_id = location_api.assetlocation_exists(projectsite, location)

            if not location_id:
                raise IOError("Specified asset location does not exist")

        else:
            location_id = self.testlocation_exists(projectsite, location)

            if not location_id:
                raise IOError("Specified test location does not exist")

        for i, row in soilprofile.iterrows():
            soiltype_id = self.soiltype_exists(soiltype=row['Soil type'])
            if not soiltype_id:
                raise IOError("Soil type %s does not exist" % row['Soil type'])

        for i, row in soilprofile.iterrows():
            if self.soilunit_exists(projectsite=projectsite, soilunit=row["Soil unit"]):
                pass
            else:
                if create_units:
                    print("Soil unit %s does not exist, creating" % row["Soil unit"])

                    soiltype_id = self.soiltype_exists(soiltype=row['Soil type'])

                    data = {
                        'title': row["Soil unit"],
                        'projectsite': project_id,
                        'soiltype': soiltype_id
                    }
                    resp = requests.post(
                        '%s/routes/soilunit/' % SOIL_URL_PREFIX,
                        headers=self.header,
                        data=data)
                else:
                    raise IOError("Soil unit %s does not exist" % row['Soil unit'])

        soilprofile_id = self.soilprofile_exists(
            projectsite=projectsite, location=location,
            soilprofile=profile_title)
        
        data = {
            "title": profile_title,
            "description": description,
            "water_level": water_level,
            "location": location_id,
            "sampletests": [],
            "batchlabtests": [],
            "insitutests": [],
            "created_by": user_id, # pk of the user creating the object
            "modified_by": user_id, # pk of the user modifying the object,
            "additional_data": additional_data
        }
        
        if soilprofile_id:
            print("Soil profile for location %s exists. Deleting." % profile_title)
            resp_profile = requests.delete(
                '%s/routes/soilprofile/%i/' % (SOIL_URL_PREFIX, soilprofile_id),
                headers=self.header)
        
        resp_profile = requests.post(
            '%s/routes/soilprofile/' % SOIL_URL_PREFIX,
            headers=self.header,
            data=data)
        
        soilprofile_id = self.soilprofile_exists(
            projectsite=projectsite, location=location,
            soilprofile=profile_title)
        
        print("Uploading soil data for %s" % profile_title)
        # Loop over soil layers and write them
        for i, layer in soilprofile.iterrows():
            try:
                _description = layer['Description']
            except:
                _description = ""
            layer_data = {
                "start_depth": layer['Depth from [m]'],
                "end_depth": layer['Depth to [m]'],
                "description": _description,
                "totalunitweight": layer['Total unit weight [kN/m3]'],
                "soilparameters": layer.drop(drop_cols).to_json(),
                "profile": soilprofile_id,
                "soilunit": self.soilunit_exists(projectsite=projectsite, soilunit=row["Soil unit"])
                    }
            resp = requests.post(
                '%s/routes/soillayer/' % SOIL_URL_PREFIX,
                headers=self.header,
                data=layer_data)

        return resp_profile