FROM binstar/miniconda
MAINTAINER Sean Ross-Ross <srossross@gmail.com>

RUN conda config --set always_yes true
RUN conda config --set binstar_upload false
RUN conda config --add channels binstar
RUN conda install conda-build jinja2 binstar binstar-build psutil
RUN binstar config --set default_site alpha
