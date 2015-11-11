
FROM binstar/build-base:centos6


RUN yum install -y gcc gcc-c++

MAINTAINER Sean Ross-Ross <srossross@gmail.com>

RUN useradd anaconda

RUN chown anaconda:anaconda -R /opt/miniconda

USER anaconda
WORKDIR /home/anaconda

ENV HOME /home/anaconda
ENV PATH /opt/miniconda/bin:$PATH



RUN conda config --set always_yes true && \
    conda config --set binstar_upload false && \
    conda config --add channels binstar
RUN conda install conda-build jinja2 anaconda-client psutil anaconda-build llvm

