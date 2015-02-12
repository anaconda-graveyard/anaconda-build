"""

"""

import logging
import os
import pipes
import shlex
import jinja2

from binstar_build_client.utils import get_conda_root_prefix

try:
    unicode
except NameError:
    unicode = str

log = logging.getLogger(__name__)

#===============================================================================
# Script exit Codes
#===============================================================================
EXIT_CODE_OK = 0
EXIT_CODE_ERROR = 11
EXIT_CODE_FAILED = 12

#===============================================================================
# Helper functions
#===============================================================================

def get_channels(job_data):
    """
    Return channel string to pass to binstar upload
    """

    build_targets = job_data['build_item_info'].get('build_targets')

    # TODO use git branch
    branch = 'dev'.replace('/', ':')
    ctx = dict(branch=branch)

    if job_data['build_info'].get('channels'):
        channels = job_data['build_info'].get('channels')
    elif isinstance(build_targets, dict):
        channels = build_targets.get('channels', [branch])
    else:
        channels = [branch]

    if not isinstance(channels, list): channels = [channels]
    _channels = []

    for ch in channels:
        try: _channels.append(ch % ctx)
        except (KeyError, ValueError):
            log.info('Bad channel value %r' % ch)

    channels = ' --channel ' + ' --channel '.join(_channels) if _channels else ''
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

def create_exports(build_data):
    """
    Create a dict of environment variables for the build script
    """
    conda_root_prefix = get_conda_root_prefix()
    build_item = build_data['build_item_info']
    build = build_data['build_info']

    api_site = build['api_endpoint']

    exports = {
            # The build number as MAJOR.MINOR
            'BINSTAR_BUILD': build_item['build_no'],
            'BINSTAR_BUILD_MAJOR': build['build_no'],
            'BINSTAR_BUILD_MINOR': build_item['sub_build_no'],
            # the engine from the engine tag
            'BINSTAR_ENGINE': build_item.get('engine'),
            # the platform from the platform tag
            'BINSTAR_PLATFORM': build_item.get('platform', 'linux-64'),
            'BINSTAR_API_SITE': api_site,
            'BINSTAR_OWNER': build_data['owner']['login'],
            'BINSTAR_PACKAGE': build_data['package']['name'],
            'BINSTAR_BUILD_ID': build['_id'],
            'CONDA_BUILD_DIR': os.path.join(conda_root_prefix, 'conda-bld', build_item.get('platform', 'linux-64')),
            'BUILD_BASE': 'builds',
            'BUILD_ENV_DIR': 'build_envs',
           }


    build_env = build_item.get('env')
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

#===============================================================================
# Generate
#===============================================================================

def gen_build_script(build_data, **context):
    """
    Generate a build script from a submitted build
    
    :return: the filename of the build script to execute
    """

    platform = build_data['build_item_info']['platform']
    job_id = build_data['job']['_id']

    env = jinja2.Environment(loader=jinja2.PackageLoader(__name__, 'data'))
    env.globals.update(get_list=get_list, quote=lambda item: pipes.quote(str(item)))

    if platform in ['win-32', 'win-64']:
        build_script_template = env.get_or_select_template('build_script.bat')
        script_filename = os.path.join('build_scripts', '%s.bat' % job_id)
    else:
        build_script_template = env.get_or_select_template('build_script.sh')
        script_filename = os.path.join('build_scripts', '%s.sh' % job_id)


    exports = create_exports(build_data)

    context.update({'exports': sorted(exports.items()),
                    'instructions': build_data['build_item_info'].get('instructions', {}),
                    'git_info': create_git_context(build_data['build_info']),
                    'test_only': build_data['build_info'].get('test_only', False),
                    'sub_dir': build_data['build_info'].get('sub_dir'),
                    'channels': get_channels(build_data),
                    'files': get_files(context, build_data),
                    'EXIT_CODE_OK': 0,
                    'EXIT_CODE_ERROR': 11,
                    'EXIT_CODE_FAILED': 12,
               })



    build_script = build_script_template.render(**context)

    if not os.path.isdir('build_scripts'):
        os.mkdir('build_scripts')

    with open(script_filename, 'w') as fd:
        fd.write(build_script)

    if os.name != 'nt':
        os.chmod(script_filename, 0o777)

    return script_filename

