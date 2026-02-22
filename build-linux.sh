#!/usr/bin/env bash
set -euo pipefail

cp CMakeLists.txt.GITHUB CMakeLists.txt

ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
DEPS_DIR="${ROOT}/depends"
CACHE_DIR="${DEPENDS_CACHE_DIR:-${ROOT}/depends-cache/linux}" 

mkdir -p "${DEPS_DIR}" "${CACHE_DIR}"

FFTW_LIB="${CACHE_DIR}/libfftw3.a"
LGBM_LIB="${CACHE_DIR}/lib_lightgbm.a"
LUNA_LIB="${CACHE_DIR}/libluna.a"

if [[ -f "${FFTW_LIB}" && -f "${LGBM_LIB}" && -f "${LUNA_LIB}" ]]; then
  echo "Using cached native dependencies from ${CACHE_DIR}"
  cp "${FFTW_LIB}" "${DEPS_DIR}/"
  cp "${LGBM_LIB}" "${DEPS_DIR}/"
  cp "${LUNA_LIB}" "${DEPS_DIR}/"
  echo "CACHE_DIR=${CACHE_DIR}"
  ls -la "${CACHE_DIR}"
  ls -l "${DEPS_DIR}"
  exit 0
fi

yum check-update || true
yum install -y curl

# CMAKE
cd "${ROOT}"
curl -O https://cmake.org/files/v3.31/cmake-3.31.0.tar.gz
tar -xzvf cmake-3.31.0.tar.gz
cd cmake-3.31.0
./bootstrap -- -DCMAKE_USE_OPENSSL=OFF
make -j2
make install

cmake --version

# LightGBM
cd "${DEPS_DIR}"
rm -rf LightGBM
git clone --recursive https://github.com/microsoft/LightGBM
cd LightGBM
mkdir -p build
cd build
cmake -DBUILD_STATIC_LIB=ON -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DUSE_OPENMP=OFF ..
make -j4
cd ..
cp lib_lightgbm.a "${DEPS_DIR}/"
cp lib_lightgbm.a "${LGBM_LIB}"

# FFTW
cd "${DEPS_DIR}"
rm -rf fftw-3.3.10 fftw-3.3.10.tar.gz
curl -O https://www.fftw.org/fftw-3.3.10.tar.gz
tar -xzvf fftw-3.3.10.tar.gz
cd fftw-3.3.10
./configure --with-pic
make -j4 CFLAGS=-fPIC
make install
ls -l .libs/
cp .libs/libfftw3.a "${DEPS_DIR}/"
cp .libs/libfftw3.a "${FFTW_LIB}"

# luna-base
cd "${DEPS_DIR}"
rm -rf luna-base
git clone https://github.com/remnrem/luna-base.git
cd luna-base
make -j4 ARCH=MAC LGBM=1 LGBM_PATH=../LightGBM/
cp libluna.a "${DEPS_DIR}/"
cp libluna.a "${LUNA_LIB}"

echo "CACHE_DIR=${CACHE_DIR}"
ls -la "${CACHE_DIR}"
ls -l "${DEPS_DIR}"
