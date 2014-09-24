"""
Remove all conda build artifacts
"""

from __future__ import print_function
import  conda_build.config
import shutil
from argparse import ArgumentParser
import os

def main():
    parser = ArgumentParser(description=__doc__)
    parser.parse_args()
    if os.path.isdir(conda_build.config.croot):
        print("Removing conda build root %s" % conda_build.config.croot)
        shutil.rmtree(conda_build.config.croot)
    else:
        print("Conda build root %s does not exist" % conda_build.config.croot)



if __name__ == '__main__':
    main()
