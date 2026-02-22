#!/usr/bin/env bash
set -euo pipefail

cp CMakeLists.txt.MAC_x86 CMakeLists.txt

ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
DEPS_DIR="${ROOT}/depends"
CACHE_DIR="${DEPENDS_CACHE_DIR:-${ROOT}/depends-cache/macos}"
MODE="${NATIVE_DEPS_MODE:-lunapi}"

mkdir -p "${DEPS_DIR}" "${CACHE_DIR}"

# ensure writable install paths exist
sudo mkdir -p /usr/local/include
sudo mkdir -p /usr/local/bin
sudo mkdir -p /usr/local/lib

FFTW_LIB="${CACHE_DIR}/libfftw3.a"
FFTW_HDR="${CACHE_DIR}/fftw3.h"
LGBM_LIB="${CACHE_DIR}/lib_lightgbm.a"
LUNA_LIB="${CACHE_DIR}/libluna.a"
LGBM_INCLUDE_CACHE="${CACHE_DIR}/LightGBM-include"
LUNA_BASE_CACHE="${CACHE_DIR}/luna-base"
DEPS_INCLUDE_CACHE="${CACHE_DIR}/include"

case "${MODE}" in
  all|luna|lunapi) ;;
  *)
    echo "Unsupported NATIVE_DEPS_MODE='${MODE}'. Expected one of: all, luna, lunapi"
    exit 2
    ;;
esac

echo "Native dependency mode: ${MODE}"

have_fftw_cache() {
  [[ -f "${FFTW_LIB}" && -f "${FFTW_HDR}" ]]
}

have_lgbm_cache() {
  [[ -f "${LGBM_LIB}" && -d "${LGBM_INCLUDE_CACHE}" ]]
}

have_luna_cache() {
  [[ -f "${LUNA_LIB}" && -d "${LUNA_BASE_CACHE}" ]]
}

restore_fftw() {
  sudo cp "${FFTW_LIB}" /usr/local/lib/
  sudo cp "${FFTW_HDR}" /usr/local/include/
}

restore_lgbm() {
  sudo cp "${LGBM_LIB}" /usr/local/lib/
  mkdir -p "${DEPS_DIR}/LightGBM"
  rm -rf "${DEPS_DIR}/LightGBM/include"
  cp -R "${LGBM_INCLUDE_CACHE}" "${DEPS_DIR}/LightGBM/include"
}

restore_luna() {
  sudo cp "${LUNA_LIB}" /usr/local/lib/
  rm -rf "${DEPS_DIR}/luna-base"
  cp -R "${LUNA_BASE_CACHE}" "${DEPS_DIR}/luna-base"
}

restore_optional_dep_include() {
  if [[ -d "${DEPS_INCLUDE_CACHE}" ]]; then
    rm -rf "${DEPS_DIR}/include"
    cp -R "${DEPS_INCLUDE_CACHE}" "${DEPS_DIR}/include"
  fi
}

save_cache_payload() {
  rm -rf "${LGBM_INCLUDE_CACHE}" "${LUNA_BASE_CACHE}" "${DEPS_INCLUDE_CACHE}"
  cp -R "${DEPS_DIR}/LightGBM/include" "${LGBM_INCLUDE_CACHE}"
  cp -R "${DEPS_DIR}/luna-base" "${LUNA_BASE_CACHE}"
  if [[ -d "${DEPS_DIR}/include" ]]; then
    cp -R "${DEPS_DIR}/include" "${DEPS_INCLUDE_CACHE}"
  fi
  echo "CACHE_DIR=${CACHE_DIR}"
  ls -la "${CACHE_DIR}"
  ls -la "${DEPS_DIR}" || true
  ls -lrt /usr/local/lib
  ls -lrt /usr/local/include
}

if [[ "${MODE}" == "lunapi" ]]; then
  if ! have_fftw_cache || ! have_lgbm_cache || ! have_luna_cache; then
    echo "lunapi mode requires cached FFTW/LGBM/luna-base artifacts, but cache is incomplete"
    echo "have_fftw_cache=$(have_fftw_cache && echo true || echo false)"
    echo "have_lgbm_cache=$(have_lgbm_cache && echo true || echo false)"
    echo "have_luna_cache=$(have_luna_cache && echo true || echo false)"
    exit 1
  fi
  echo "Using cached native dependencies from ${CACHE_DIR} (lunapi-only mode)"
  restore_fftw
  restore_lgbm
  restore_luna
  restore_optional_dep_include
  echo "CACHE_DIR=${CACHE_DIR}"
  ls -la "${CACHE_DIR}"
  ls -la "${DEPS_DIR}" || true
  ls -lrt /usr/local/lib
  ls -lrt /usr/local/include
  exit 0
fi

if [[ "${MODE}" == "luna" ]]; then
  if ! have_fftw_cache || ! have_lgbm_cache; then
    echo "luna mode requires cached FFTW/LGBM artifacts, but cache is incomplete"
    echo "have_fftw_cache=$(have_fftw_cache && echo true || echo false)"
    echo "have_lgbm_cache=$(have_lgbm_cache && echo true || echo false)"
    exit 1
  fi
  echo "Using cached FFTW/LGBM and rebuilding luna-base"
  restore_fftw
  restore_lgbm
  restore_optional_dep_include
fi

if [[ "${MODE}" == "all" ]]; then
  echo "Rebuilding FFTW, LightGBM, and luna-base from scratch"
fi

# all/luna modes both build luna-base below. all mode also rebuilds FFTW/LGBM first.
if [[ "${MODE}" == "all" ]]; then
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
  restore_fftw

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
fi

# luna-base (built in all/luna modes)
cd "${DEPS_DIR}"
rm -rf luna-base
git clone https://github.com/remnrem/luna-base.git
cd luna-base
make -j4 ARCH=MAC LGBM=1 LGBM_PATH=../LightGBM/
sudo cp libluna.a /usr/local/lib/
cp libluna.a "${LUNA_LIB}"

save_cache_payload
exit 0
