
FROM quay.io/jupyter/datascience-notebook

USER root

WORKDIR /build

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y git g++ less emacs nano wget zlib1g-dev fftw3-dev libgit2-dev libssl-dev libssh2-1-dev libxml2-dev libcurl4-openssl-dev

#install latest cmake
ADD https://cmake.org/files/v3.22/cmake-3.22.2-linux-x86_64.sh /cmake-3.22.2-linux-x86_64.sh

RUN mkdir /opt/cmake \
 && sh /cmake-3.22.2-linux-x86_64.sh --prefix=/opt/cmake --skip-license \
 && ln -s /opt/cmake/bin/cmake /usr/local/bin/cmake \
 && ln -s /opt/cmake/bin/cmake /usr/bin/cmake \
 && cmake --version

RUN git clone --recursive https://github.com/microsoft/LightGBM \
 && cd LightGBM \
 && mkdir build \
 && cd build \
 && cmake .. \
 && make -j4 \
 && cp ../lib_lightgbm.so /usr/local/lib/

RUN cd /build \
 && git clone https://gitlab-scm.partners.org/zzz-public/nsrr.git

RUN mkdir /data \
 && mkdir /data1 \
 && mkdir /data2 \
 && mkdir /tutorial \
 && cd /tutorial \
 && wget https://zzz.bwh.harvard.edu/dist/luna/tutorial.zip \
 && unzip tutorial.zip \
 && rm tutorial.zip

RUN cd /home/jovyan/ \
  && pip install pybind11 

ENV LD_LIBRARY_PATH=/usr/local/lib/

# force rebuild of lunapi below
ADD "https://www.random.org/cgi-bin/randbyte?nbytes=10&format=h" skipcache

RUN cd /build \
 && git clone https://github.com/remnrem/luna-base.git \
 && cd luna-base \
 && make -j 2 LGBM=1 LGBM_PATH=/build/LightGBM \
 && ln -s /build/luna-base/luna /usr/local/bin/luna \
 && ln -s /build/luna-base/destrat /usr/local/bin/destrat \
 && ln -s /build/luna-base/behead /usr/local/bin/behead \
 && ln -s /build/luna-base/fixrows /usr/local/bin/fixrows \
 && sudo cp libluna.so /usr/local/lib/

RUN cd /build \
 && git clone https://github.com/remnrem/luna-api.git \
 && cd luna-api \
 && g++ -O3 -Wall -shared -std=c++17 -fPIC \
     -I../luna-base/ -I../luna-base/stats \
     $(python3 -m pybind11 --includes) \
     -Wno-sign-compare \
     `python3-config --ldflags` \
     lunapi.cpp \
     -o lunapi$(python3-config --extension-suffix) \
     -lluna -l_lightgbm -lfftw3 -lz

ENV PYTHONPATH=/build/luna-api

USER jovyan

WORKDIR /lunapi

# CMD [ "/bin/bash" ]
