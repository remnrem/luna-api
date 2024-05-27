FROM quay.io/jupyter/minimal-notebook

USER root

WORKDIR /build

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y git g++ less emacs nano wget micro libomp5 cmake fftw3-dev libomp-dev

RUN git clone --recursive https://github.com/microsoft/LightGBM \
 && cd LightGBM \
 && mkdir build \
 && cd build \
 && cmake .. \
 && make -j4 \
 && cp ../lib_lightgbm.so /usr/local/lib/

RUN cd /build \
 && git clone https://gitlab-scm.partners.org/zzz-public/nsrr.git

RUN wget https://www.fftw.org/fftw-3.3.10.tar.gz \
 && tar xzvf fftw-3.3.10.tar.gz \
 && cd fftw-3.3.10 \
 && ./configure --enable-shared \
 && make \
 && make install \
 && ls -la \
 && ls -l .libs/ \
 && cp .libs/libfftw3.so /usr/local/lib/

RUN cd /home/jovyan/ \
  && pip install pybind11

ENV LD_LIBRARY_PATH=/usr/local/lib/

RUN apt-get install -y 

RUN mkdir /data \
 && mkdir /data1 \
 && mkdir /data2 \
 && cd / \
 && wget https://zzz.bwh.harvard.edu/dist/luna/tutorial.zip \
 && unzip tutorial.zip \
 && rm tutorial.zip

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
 && sudo cp libluna.a /usr/local/lib/


# make lunapi 
RUN pip install pandas matplotlib plotly ipywidgets \
 && cd /build \
 && git clone https://github.com/remnrem/luna-api.git \
 && cd luna-api \
 && cp CMakeLists.txt.docker CMakeLists.txt \
 && pip install . 

USER jovyan

WORKDIR /lunapi

RUN ln -s /tutorial /lunapi/tutorial

ENV PYTHONPATH=/build/luna-api
