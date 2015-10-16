from __future__ import (print_function, unicode_literals, division,
    absolute_import)

import base64
import json
import os
import requests
import warnings

from binstar_build_client.mixins.build import BuildMixin
from binstar_build_client.mixins.build_queue import BuildQueueMixin
import logging
from binstar_client import Binstar

log = logging.getLogger('binstar.build')


class BinstarBuildAPI(BuildMixin, BuildQueueMixin, Binstar):
    '''
    '''
    pass

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
