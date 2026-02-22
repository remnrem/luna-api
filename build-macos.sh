#!/usr/bin/env bash
set -euo pipefail

cp CMakeLists.txt.MAC_x86 CMakeLists.txt

ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
DEPS_DIR="${ROOT}/depends"
CACHE_DIR="${DEPENDS_CACHE_DIR:-${ROOT}/depends-cache/macos}"

mkdir -p "${DEPS_DIR}" "${CACHE_DIR}"

# ensure writable install paths exist
sudo mkdir -p /usr/local/include
sudo mkdir -p /usr/local/bin
sudo mkdir -p /usr/local/lib

FFTW_LIB="${CACHE_DIR}/libfftw3.a"
FFTW_HDR="${CACHE_DIR}/fftw3.h"
LGBM_LIB="${CACHE_DIR}/lib_lightgbm.a"
LUNA_LIB="${CACHE_DIR}/libluna.a"

if [[ -f "${FFTW_LIB}" && -f "${FFTW_HDR}" && -f "${LGBM_LIB}" && -f "${LUNA_LIB}" ]]; then
  echo "Using cached native dependencies from ${CACHE_DIR}"
  sudo cp "${FFTW_LIB}" /usr/local/lib/
  sudo cp "${FFTW_HDR}" /usr/local/include/
  sudo cp "${LGBM_LIB}" /usr/local/lib/
  sudo cp "${LUNA_LIB}" /usr/local/lib/
  echo "CACHE_DIR=${CACHE_DIR}"
  ls -la "${CACHE_DIR}"
  ls -lrt /usr/local/lib
  ls -lrt /usr/local/include
  exit 0
fi

# FFTW
cd "${DEPS_DIR}"
rm -rf fftw-3.3.10 fftw-3.3.10.tar.gz
curl -L -o fftw-3.3.10.tar.gz https://www.fftw.org/fftw-3.3.10.tar.gz
tar -xzvf fftw-3.3.10.tar.gz
cd fftw-3.3.10
./configure --with-pic
make -j4 CFLAGS=-fPIC
sudo make install
cp .libs/libfftw3.a "${FFTW_LIB}"
cp api/fftw3.h "${FFTW_HDR}"

# LightGBM
cd "${DEPS_DIR}"
rm -rf LightGBM
git clone --recursive https://github.com/microsoft/LightGBM
cd LightGBM
mkdir -p build
cd build
cmake -DBUILD_STATIC_LIB=ON -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DUSE_OPENMP=OFF ..
make -j4
sudo cp ../lib_lightgbm.a /usr/local/lib/
cp ../lib_lightgbm.a "${LGBM_LIB}"

# luna-base
cd "${DEPS_DIR}"
rm -rf luna-base
git clone https://github.com/remnrem/luna-base.git
cd luna-base
make -j4 ARCH=MAC LGBM=1 LGBM_PATH=../LightGBM/
sudo cp libluna.a /usr/local/lib/
cp libluna.a "${LUNA_LIB}"

echo "CACHE_DIR=${CACHE_DIR}"
ls -la "${CACHE_DIR}"
ls -lrt /usr/local/lib
ls -lrt /usr/local/include
