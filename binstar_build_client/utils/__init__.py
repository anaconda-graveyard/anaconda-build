

import os
import sys
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

CONDA_EXE = 'conda.exe' if os.name == 'nt' else 'conda'

def get_conda_root_prefix():
    """
    get the directory prefix to where conda is installed
    """
    canonical_dir_current_executable = os.path.dirname(os.path.realpath(sys.executable))
    paths = [canonical_dir_current_executable, ] + os.environ.get('PATH').split(os.pathsep)

    for entry in paths:
        if os.path.isdir(entry) and CONDA_EXE in os.listdir(entry):
            conda_exe_path = os.path.realpath(os.path.join(entry, 'conda'))
            bin_dir = os.path.dirname(conda_exe_path)
            return os.path.dirname(bin_dir)

def get_anaconda_url(binstar, path):
    '''
    Gets an absolute URL to the `path` identified

    Args:
        binstar: the BinstarAPI client
        path: the anaconda repository relative URL

    Returns:
        (str) an absolute URL

    Examples:

        >>> from binstar_client import Binstar
        >>> get_anaconda_url(Binstar(domain='http://127.0.0.1:8080/api'), '/me/builds')
        'http://127.0.0.1:8080/me/builds'
        >>> get_anaconda_url(Binstar(), '/me/builds')
        'https://anaconda.org/me/builds'

    '''
    url = urlparse(binstar.domain)
    netloc = url.netloc
    if netloc.startswith('api.'):
        netloc = netloc.replace('api.', '')

    scheme = url.scheme

    return '{scheme}://{netloc}{path}'.format(
        scheme=scheme,
        netloc=netloc,
        path=path,
    )
