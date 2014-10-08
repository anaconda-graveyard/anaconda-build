import make_version
from setuptools import setup, find_packages

ctx = {}
version = make_version.pypi_version()

setup(
    name='binstar-build',
    version=version,
    author='Sean Ross-Ross',
    author_email='srossross@gmail.com',
    url='http://github.com/Binstar/binstar_client',
    packages=find_packages(),
    install_requires=['requests',
                      'pyyaml',
                      'python-dateutil',
                      'pytz',
                      'jinja2'],

    include_package_data=True,
    zip_safe=False,

    entry_points={
          'console_scripts': [
              'binstar-build = binstar_build_client.scripts.build:main',
              'conda-clean-build-dir = binstar_build_client.scripts.conda_clean_build_dir:main',
              ]
                 },

)
