
FROM binstar/build-base:centos6


RUN yum install -y gcc gcc-c++ patch subversion

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
RUN anaconda config --set url https://api.anaconda.org
USER root
WORKDIR /root

RUN yum install -y curl-devel expat-devel gettext-devel openssl-devel zlib-devel perl-ExtUtils-MakeMaker
RUN yum remove -y git && \
    wget -q https://www.kernel.org/pub/software/scm/git/git-2.1.0.tar.gz && \
    tar -xzf git-2.1.0.tar.gz && \
    cd git-2.1.0 && \
    make prefix=/usr/local/git all && \
    make prefix=/usr/local/git install && \
    echo "export PATH=\$PATH:/usr/local/git/bin" >> /etc/bashrc && \
    ln -s /usr/local/git/bin/git /usr/bin/git


