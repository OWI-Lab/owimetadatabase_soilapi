from re import sub
import requests
from copy import deepcopy
import numpy as np
import pandas as pd


class API(object):

    def __init__(self, api_root, header=None, uname=None, password=None):

        self.api_root = api_root
        self.header = header
        self.uname = uname
        self.password = password
        if self.uname is not None and self.password is not None:
            self.auth = requests.auth.HTTPBasicAuth(self.uname, self.password)
        else:
            self.auth = None