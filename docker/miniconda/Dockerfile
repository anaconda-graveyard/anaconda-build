FROM centos:centos6
MAINTAINER Sean Ross-Ross <srossross@gmail.com>

RUN yum install -y tar bzip2
RUN yum install -y ntp chrpath wget dos2unix gcc gcc-c++ 
RUN yum install -y git

RUN curl http://repo.continuum.io/miniconda/Miniconda-3.7.0-Linux-x86_64.sh > miniconda.sh
RUN bash miniconda.sh -b -p /opt/miniconda
RUN rm miniconda.sh
ENV PATH /opt/miniconda/bin:$PATH
