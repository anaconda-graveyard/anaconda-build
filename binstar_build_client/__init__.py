from __future__ import unicode_literals
import base64
import json
import os
import requests
import warnings

from binstar_client.mixins.build import BuildMixin
from binstar_client.utils.http_codes import STATUS_CODES
import logging
from binstar_client import Binstar

log = logging.getLogger('binstar.build')

from ._version import __version__

class BinstarBuildAPI(BuildMixin, Binstar):
    '''
    '''
    pass

