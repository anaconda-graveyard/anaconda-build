FROM continuumio/anaconda-build-64
MAINTAINER Peter Steinberg <psteinberg@continuum.io>

USER root
RUN echo 'Defaults:dev   !requiretty' >> /etc/sudoers

USER dev
ENV ARCH=32
