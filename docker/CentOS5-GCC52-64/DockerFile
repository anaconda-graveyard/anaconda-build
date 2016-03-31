FROM continuumio/conda_builder_linux:5.11-5.2-0-0
MAINTAINER Peter Steinberg <psteinberg@continuum.io>

USER root
RUN yum install -y subversion

RUN /opt/miniconda/bin/conda config --set always_yes true && \
    /opt/miniconda/bin/conda config --set anaconda_upload false

RUN /opt/miniconda/bin/conda install anaconda-build

USER dev
# Use the C++98 ABI by default
ENV ABI=4
# The startup script will setup the environment correctly for us -
# CFLAGS/CXXFLAGS, as well as some other bits and bobs
ENTRYPOINT ["/opt/share/internal_startup.sh"]
