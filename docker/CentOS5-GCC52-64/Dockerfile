FROM continuumio/conda_builder_linux:5.11-5.2-1-0
MAINTAINER Peter Steinberg <psteinberg@continuum.io>

USER root
# Subversion is required to support `svn_url` for conda-build
RUN yum install -y subversion && yum clean all

# Automated build should not prompt for installs, and should not
# submit builds automatically
RUN /opt/miniconda/bin/conda config --set always_yes true && \
    /opt/miniconda/bin/conda config --set anaconda_upload false

# Install anaconda-build
RUN /opt/miniconda/bin/conda update --all && \
    /opt/miniconda/bin/conda install anaconda-build && \
    /opt/miniconda/bin/conda clean --all

# We need git when the root environment is inactive
RUN /bin/ln -sf /opt/miniconda/bin/git /usr/local/bin/git

# Run as unprivileged user
USER dev
# Use the C++98 ABI by default
ENV ABI=4
# The startup script will setup the environment correctly for us -
# CFLAGS/CXXFLAGS, as well as some other bits and bobs
ENTRYPOINT ["/opt/share/internal_startup.sh"]
