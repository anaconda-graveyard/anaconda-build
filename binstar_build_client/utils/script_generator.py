import jinja2
import pipes
import shlex


def get_list(dct, item, default=()):
    """
    Get an item from a dictionary, like `dict.get`. 
    
    This method will transform all scalar values into lists of lenght 1
    """
    value = dct.get(item, default)
    if not isinstance(value, (list, tuple)): value = [value]
    return list(value)

def create_git_context(build):
    git_info = {}
    github_info = build.get('github_info', {})
    if github_info:
        git_info['full_name'] = '%s/%s' % (github_info['repository']['owner']['name'], github_info['repository']['name'])
        git_info['branch'] = github_info['ref'].split('/', 2)[-1]
        git_info['commit'] = github_info['after']
    return git_info

def create_exports(build_data):

    build_item = build_data['build_item_info']
    build = build_data['build_info']

    api_site = build['api_endpoint']
    quote_str = lambda item: pipes.quote(str(item))
    exports = {
            # The build number as MAJOR.MINOR
            'BINSTAR_BUILD': quote_str(build_item['build_no']),
            'BINSTAR_BUILD_MAJOR': quote_str(build['build_no']),
            'BINSTAR_BUILD_MINOR': quote_str(build_item['sub_build_no']),
            # the engine from the engine tag
            'BINSTAR_ENGINE': build_item.get('engine'),
            # the platform from the platform tag
            'BINSTAR_PLATFORM': build_item.get('platform', 'linux-64'),
            'BUILD_ENV_PATH': "/opt/anaconda/envs/install",
            'BINSTAR_API_SITE': quote_str(api_site),
            'BINSTAR_OWNER': quote_str(build_data['owner']['login']),
            'BINSTAR_PACKAGE': quote_str(build_data['package']['name']),
            'BINSTAR_BUILD_ID': quote_str(build['_id']),
           }

    build_env = build_item.get('env')

    if isinstance(build_env, str):
        _build_env = {}
        for item in shlex.split(build_env):
            if '=' in item:
                key, value = item.split('=', 1)
                _build_env[key] = value

        build_env = _build_env

    if build_env:
        exports.update(build_env)
    return exports

def gen_build_script(build_data, **context):
    """
    Generate a build script from a submitted build
    """

    env = jinja2.Environment(loader=jinja2.PackageLoader(__name__, 'data'))
    env.globals.update(get_list=get_list, quote=pipes.quote)
    build_script = env.get_or_select_template('build_script.sh')

    exports = create_exports(build_data)

    context.update({'exports': sorted(exports.items()),
                    'instructions': build_data['build_item_info'].get('instructions', {}),
                    'git_info': create_git_context(build_data['build_info']),
                    'test_only': build_data['build_info'].get('test_only', False),
                    'sub_dir': build_data['build_info'].get('sub_dir')
               })

    return build_script.render(**context)

