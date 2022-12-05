# -*- coding: utf-8 -*-

__author__ = 'Bruno Stuyts'

# Native Python packages
import json

# 3rd party packages
import pandas as pd
import requests
import plotly.express as px

# Project imports
from owimetadatabase_soilapi.io import API


LOCATION_URL_PREFIX = "https://owimetadatabase.owilab.be/api/v1/locations"


class LocationsAPI(API):
    """
    Class to connect to the location data API with methods to retrieve data

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


    def get_projectsites(self, **kwargs):
        """
        Get all available projects

        :return:  Dictionary with the following keys:

            - 'data': Pandas dataframe with the location data for each project
            - 'exists': Boolean indicating whether matching records are found
        """
        url_params = {}

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/projectsites/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            df = pd.DataFrame()

        if df.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df,
            'exists': exists
        }

    def get_projectsite_detail(self, projectsite, **kwargs):
        """
        Get details for a specific projectsite

        :param projectsite: Title of the projectsite
        :return:  Dictionary with the following keys:

            - 'id': id of the selected project site
            - 'data': Pandas dataframe with the location data for each projectsite
            - 'exists': Boolean indicating whether matching records are found
        """
        url_params = self.urlparameters(
            parameters=[projectsite, ],
            parameternames=['projectsite', ]
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/projectsites/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            df = pd.DataFrame()

        if df.__len__() == 0:
            exists = False
            project_id = None
        elif df.__len__() == 1:
            exists = True
            project_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one project site was returned, check search criteria.")

        return {
            'id': project_id,
            'data': df,
            'exists': exists
        }

    def projectsite_exists(self, projectsite, **kwargs):
        """
        Checks if the project site answering to the search criteria exists

        :param projectsite: Title of the project site
        
        :return: Returns the id if the sample test exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[projectsite,],
            parameternames=['projectsite',]
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/projectsite/' % self.api_root,
            headers=self.header,
            params=url_params)
        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            df = pd.DataFrame()

        if df.__len__() == 0:
            record_id = False
        elif df.__len__() == 1:
            record_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one project site test was returned, refine search criteria")

        return record_id


    def get_assetlocations(self, projectsite=None, assetlocation=None, **kwargs):
        """
        Get all available asset locations, specify a projectsite or filter by projectsite

        :param projectsite: String with the projectsite title (e.g. "HKN")
        :param assetlocation: String with the asset location title (e.g. "HKNA01")
        :return: Dictionary with the following keys:

            - 'data': Pandas dataframe with the location data for each location in the projectsite
            - 'exists': Boolean indicating whether matching records are found
        """
        url_params = self.urlparameters(
            parameters=[projectsite, assetlocation],
            parameternames=['projectsite', 'assetlocation']
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/assetlocations/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            df = pd.DataFrame()

        if df.__len__() == 0:
            exists = False
        else:
            exists = True

        return {
            'data': df,
            'exists': exists
        }

    def get_assetlocation_detail(self, projectsite, assetlocation, **kwargs):
        """
        Get a selected turbine

        :param projectsite: Name of the projectsite (e.g. "HKN")
        :param assetlocation: Title of the asset location (e.g. "HKN-A01")
        
        :return: Dictionary with the following keys:

            - 'id': id of the selected projectsite site
            - 'data': Pandas dataframe with the location data for the individual location
            - 'exists': Boolean indicating whether a matching location is found
        """
        url_params = self.urlparameters(
            parameters=[projectsite, assetlocation],
            parameternames=['projectsite', 'assetlocation']
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/assetlocations/' % self.api_root,
            headers=self.header,
            params=url_params)

        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            df = pd.DataFrame()

        if df.__len__() == 0:
            exists = False
            assetlocation_id = None
        elif df.__len__() == 1:
            exists = True
            assetlocation_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one asset location was returned, check search criteria.")

        return {
            'id': assetlocation_id,
            'data': df,
            'exists': exists
        }

    def assetlocation_exists(self, projectsite, assetlocation, **kwargs):
        """
        Checks if the asset location answering to the search criteria exists

        :param projectsite: Title of the project site
        :param assetlocation: Title of the asset location (e.g. "BBK05")
        
        :return: Returns the id if the asset location exists, False otherwise
        """
        url_params = self.urlparameters(
            parameters=[projectsite, assetlocation],
            parameternames=['projectsite', 'assetlocation']
        )

        url_params = {**url_params, **kwargs}

        resp = requests.get(
            url='%s/assetlocations/' % self.api_root,
            headers=self.header,
            params=url_params)
        try:
            df = pd.DataFrame(json.loads(resp.text))
        except:
            df = pd.DataFrame()

        if df.__len__() == 0:
            record_id = False
        elif df.__len__() == 1:
            record_id = df['id'].iloc[0]
        else:
            raise ValueError("More than one asset location was returned, refine search criteria")

        return record_id

    def plot_assetlocations(self, return_fig=False, **kwargs):
        """
        Retrieves asset locations and generates a Plotly plot to show them

        :param return_fig: Boolean indicating whether the Plotly figure object needs to be returned (default is False which simply shows the plot)
        :param kwargs: Keyword arguments for the search (see ``get_assetlocations``)

        :return: Plotly figure object with selected asset locations plotted on OpenStreetMap tiles (if requested)
        """
        assetlocations = self.get_assetlocations(**kwargs)['data']
        fig = px.scatter_mapbox(
            assetlocations,
            lat='northing',
            lon='easting',
            hover_name='title',
            hover_data=['projectsite_name', 'description'],
            zoom=9.6,
            height=500
        )
        fig.update_layout(mapbox_style="open-street-map")
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        if return_fig:
            return fig
        else:
            fig.show()