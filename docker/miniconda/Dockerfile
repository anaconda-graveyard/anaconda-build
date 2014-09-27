FROM centos:centos6
MAINTAINER Sean Ross-Ross <srossross@gmail.com>

RUN yum install -y tar bzip2
RUN useradd binstar
USER binstar
WORKDIR /home/binstar
RUN curl http://repo.continuum.io/miniconda/Miniconda-3.7.0-Linux-x86_64.sh > /home/binstar/miniconda.sh
RUN bash /home/binstar/miniconda.sh -b -p /home/binstar/miniconda
RUN rm /home/binstar/miniconda.sh
ENV PATH /home/binstar/miniconda/bin:$PATH
ENV HOME /home/binstar
