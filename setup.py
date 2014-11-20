from setuptools import setup, find_packages

ctx = {}
try:
    with open('binstar_build_client/_version.py') as fd:
        exec(open('binstar_build_client/_version.py').read(), ctx)
    version = ctx.get('__version__', 'dev')
except IOError:
    version = '0.8'

setup(
    name='binstar-build',
    version=version,
    author='Sean Ross-Ross',
    author_email='srossross@gmail.com',
    url='http://github.com/Binstar/binstar_client',
    packages=find_packages(),
    install_requires=['binstar',
                      'jinja2', 'psutil'],

    include_package_data=True,
    zip_safe=False,

    entry_points={
          'console_scripts': [
              'binstar-build = binstar_build_client.scripts.build:main',
              'conda-clean-build-dir = binstar_build_client.scripts.conda_clean_build_dir:main',
              ]
                 },

)
