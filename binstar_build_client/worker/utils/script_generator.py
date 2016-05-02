"""

"""
from __future__ import print_function, unicode_literals, absolute_import

import logging
import os
import pipes
import shlex

import jinja2

from binstar_build_client.utils import get_conda_root_prefix
from binstar_build_client.worker.utils import build_log

try:
    unicode
except NameError:
    unicode = str
    basestring = (str, bytes)

log = logging.getLogger(__name__)

# ===============================================================================
# Script exit Codes
# ===============================================================================
EXIT_CODE_OK = 0
EXIT_CODE_ERROR = 11
EXIT_CODE_FAILED = 12


# ===============================================================================
# Helper functions
# ===============================================================================

def metadata(**kwargs):
    '''
    Returns a metadata tag that is safe for inclusion in script or bat files
    '''
    return build_log.encode_metadata(kwargs)

def get_labels(job_data):
    """
    Return `--label` arguments to pass to `anaconda upload`
    """

    build_targets = job_data['build_item_info'].get('instructions', {}).get('build_targets')

    # TODO use git branch
    branch = 'dev'.replace('/', ':')
    ctx = dict(branch=branch)

    if job_data['build_info'].get('channels') or job_data['build_info'].get('labels'):
        # TODO: this is pulled from the API (pushed from anaconda-build)
        channels = job_data['build_info'].get('channels') or job_data['build_info'].get('labels')
    elif isinstance(build_targets, dict) and \
            (build_targets.get('channels') or build_targets.get('labels')):
        channels = build_targets.get('channels') or build_targets.get('labels')
    else:
        channels = [branch]

    if not isinstance(channels, list): channels = [channels]
    _channels = []

    for ch in channels:
        try:
            _channels.append(ch % ctx)
        except (KeyError, ValueError):
            log.info('Bad channel value %r' % ch)

    channels = ' --label ' + ' --label '.join(_channels) if _channels else 'dev'
    return channels


def get_files(context, job_data):
    """
    Return a list of files to run binstar upload on
    """
    build_targets = job_data['build_item_info'].get('instructions', {}).get('build_targets')
    if not build_targets:
        return []
    if isinstance(build_targets, basestring):
        build_targets = [build_targets]
    elif isinstance(build_targets, dict):
        build_targets = get_list(build_targets, 'files', default=[])

    if 'conda' in build_targets:
        idx = build_targets.index('conda')
        conda_build_dir = context['conda_build_dir']
        build_targets[idx] = os.path.join(conda_build_dir, '*.tar.bz2')

    if 'pypi' in build_targets:
        idx = build_targets.index('pypi')
        build_targets[idx] = 'dist/*'

    return build_targets


def get_force_upload(job_data):
    build_targets = job_data['build_item_info'].get('instructions', {}).get('build_targets')
    force = False
    if isinstance(build_targets, dict):
        force = build_targets.get('force_upload', False)

    return '--force' if force else ''


def get_list(dct, item, default=()):
    """
    Get an item from a dictionary, like `dict.get`.

    This method will transform all scalar values into lists of lenght 1
    """
    value = dct.get(item, default)
    if not isinstance(value, (list, tuple)): value = [value]
    return list(value)


def create_git_context(build):
    """
    Create the git_info object for git source builds
    """
    git_info = {}
    github_info = build.get('github_info', {})
    if github_info:
        ghrepo = github_info['repository']
        ghowner = ghrepo['owner'].get('name', ghrepo['owner'].get('login'))
        git_info['full_name'] = '%s/%s' % (ghowner, ghrepo['name'])
        git_info['branch'] = github_info['ref'].split('/', 2)[-1]
        git_info['commit'] = github_info['after']
    return git_info


def create_exports(build_data, working_dir):
    """
    Create a dict of environment variables for the build script
    """
    conda_root_prefix = get_conda_root_prefix()
    build_item = build_data['build_item_info']
    build = build_data['build_info']

    api_site = build['api_endpoint']
    engine = build_item.get('engine')

    CONDA_NPY = ''
    if 'numpy' in engine:
        npy_version = engine.split('numpy')[1].split()
        if npy_version:
            CONDA_NPY = "".join(npy_version[0].split('.')[:2])
            CONDA_NPY = CONDA_NPY.replace('=', '')

    exports = {
        # The build number as MAJOR.MINOR
        'BINSTAR_BUILD': build_item['build_no'],
        'BINSTAR_BUILD_MAJOR': build['build_no'],
        'BINSTAR_BUILD_MINOR': build_item['sub_build_no'],
        # the engine from the engine tag
        'BINSTAR_ENGINE': engine,
        # the platform from the platform tag
        'BINSTAR_PLATFORM': build_item.get('platform', 'linux-64'),
        'BINSTAR_API_SITE': api_site,
        'BINSTAR_OWNER': build_data['owner']['login'],
        'BINSTAR_PACKAGE': build_data['package']['name'],
        'BINSTAR_BUILD_ID': build['_id'],
        'CONDA_BUILD_DIR': os.path.join(conda_root_prefix, 'conda-bld', build_item.get('platform', 'linux-64')),
        'WORKING_DIR': working_dir,
        'CONDA_NPY': CONDA_NPY,
    }
    build_env = build_item.get('envvars', build_item.get('env'))
    if isinstance(build_env, (str, unicode)):
        _build_env = {}
        for item in shlex.split(build_env):
            if '=' in item:
                key, value = item.split('=', 1)
                _build_env[key] = value

        build_env = _build_env

    if isinstance(build_env, dict):
        exports.update(build_env)

    return exports


GLOBALS = {
    'get_list': get_list,
    'quote': lambda item: pipes.quote(str(item)),
    'metadata': metadata,
}


# ===============================================================================
# Generate
# ===============================================================================
def render_build_script(working_dir, build_data, **context):
    """
    Generate a build script from a submitted build

    :param working_dir: The working directory this build will be executed in
    :param build_data:  The job information
    :return: the content of the build script to execute
    """


    env = jinja2.Environment(loader=jinja2.PackageLoader(__name__, 'data'))
    env.globals.update(GLOBALS)

    exports = create_exports(build_data, working_dir)
    instructions = build_data['build_item_info'].get('instructions', {})
    install_channels = instructions.get('install_channels', None) or ['defaults']
    if 'defaults' not in install_channels:
        install_channels.append('defaults')
    if 'r' == exports['BINSTAR_ENGINE'] and 'r' not in install_channels:
        install_channels.append('r')

    context.update({
        'exports': sorted(exports.items()),
        'instructions': instructions,
        'git_info': create_git_context(build_data['build_info']),
        'test_only': build_data['build_info'].get('test_only', False),
        'sub_dir': build_data['build_info'].get('sub_dir'),
        'labels': get_labels(build_data),
        'files': get_files(context, build_data),
        'force_upload': get_force_upload(build_data),
        'install_channels': install_channels,
        'EXIT_CODE_OK': 0,
        'EXIT_CODE_ERROR': 11,
        'EXIT_CODE_FAILED': 12,
    })

    platform = build_data['build_item_info']['platform']
    extension = '.bat' if platform in ['win-32', 'win-64'] else '.sh'
    template_name = 'build_script' + extension
    template = env.get_or_select_template(template_name)

    return template.render(**context)


def gen_build_script(staging_dir, working_dir, build_data, **context):
    """
    Generate a build script from a submitted build

    :return: the filename of the build script to execute
    """

    build_script = render_build_script(working_dir, build_data, **context)

    platform = build_data['build_item_info']['platform']
    extension = '.bat' if platform in ['win-32', 'win-64'] else '.sh'
    script_filename = 'build_script' + extension
    script_path = os.path.join(staging_dir, script_filename)

    with open(script_path, 'w') as fd:
        fd.write(build_script)

    if os.name != 'nt':
        os.chmod(script_path, 0o777)

    return script_path
