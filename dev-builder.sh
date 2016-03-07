#!/bin/bash

rm docker/dev-builder/anaconda-build-*
python setup.py sdist --dist-dir docker/dev-builder/
VERSION=$(python -c 'import binstar_build_client; print(binstar_build_client.__version__.replace("+", "-"))')
(cd docker/dev-builder; docker build -t binstar/linux-64:$VERSION -t binstar/linux-64:dev .)
