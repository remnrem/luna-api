#!/usr/bin/env bash
set -euo pipefail

cp CMakeLists.txt.GITHUB CMakeLists.txt

ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
DEPS_DIR="${ROOT}/depends"
CACHE_DIR="${DEPENDS_CACHE_DIR:-${ROOT}/depends-cache/linux}"
MODE="${NATIVE_DEPS_MODE:-lunapi}"
QUIET="${NATIVE_DEPS_QUIET:-1}"
BUILD_LOG="${ROOT}/native-deps-build.log"

mkdir -p "${DEPS_DIR}" "${CACHE_DIR}"
: > "${BUILD_LOG}"
if [[ "${QUIET}" == "1" ]]; then
  trap 'echo "native deps build failed; tail of ${BUILD_LOG}:"; tail -n 200 "${BUILD_LOG}" || true' ERR
fi

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
  cp "${FFTW_LIB}" "${DEPS_DIR}/libfftw3.a"
  mkdir -p "${DEPS_DIR}/include"
  cp "${FFTW_HDR}" "${DEPS_DIR}/include/fftw3.h"
  if [[ -w /usr/local/lib || ! -e /usr/local/lib ]]; then
    mkdir -p /usr/local/lib
    cp "${FFTW_LIB}" /usr/local/lib/libfftw3.a
  fi
  if [[ -w /usr/local/include || ! -e /usr/local/include ]]; then
    mkdir -p /usr/local/include
    cp "${FFTW_HDR}" /usr/local/include/fftw3.h
  fi
}

restore_lgbm() {
  cp "${LGBM_LIB}" "${DEPS_DIR}/lib_lightgbm.a"
  mkdir -p "${DEPS_DIR}/LightGBM"
  cp "${LGBM_LIB}" "${DEPS_DIR}/LightGBM/lib_lightgbm.a"
  local include_src=""
  local include_dst="${DEPS_DIR}/LightGBM/include"
  if [[ -d "${LGBM_INCLUDE_CACHE}" ]]; then
    include_src="${LGBM_INCLUDE_CACHE}"
  elif [[ -d "${include_dst}" ]]; then
    # all-mode may have just built LightGBM before cache payload exists
    include_src="${include_dst}"
  else
    echo "Missing LightGBM include payload in both cache and local build tree"
    return 1
  fi
  if [[ "${include_src}" != "${include_dst}" ]]; then
    rm -rf "${include_dst}"
    cp -R "${include_src}" "${include_dst}"
  fi
}

restore_luna() {
  cp "${LUNA_LIB}" "${DEPS_DIR}/libluna.a"
  local luna_src=""
  local luna_dst="${DEPS_DIR}/luna-base"
  if [[ -d "${LUNA_BASE_CACHE}" ]]; then
    luna_src="${LUNA_BASE_CACHE}"
  elif [[ -d "${luna_dst}" ]]; then
    # all-mode may have just built luna-base before cache payload exists
    luna_src="${luna_dst}"
  else
    echo "Missing luna-base payload in both cache and local build tree"
    return 1
  fi
  if [[ "${luna_src}" != "${luna_dst}" ]]; then
    rm -rf "${luna_dst}"
    cp -R "${luna_src}" "${luna_dst}"
  fi
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

if [[ "${MODE}" == "all" ]]; then
  if ! command -v curl >/dev/null 2>&1; then
    if command -v yum >/dev/null 2>&1; then
      if [[ "${QUIET}" == "1" ]]; then
        yum check-update >> "${BUILD_LOG}" 2>&1 || true
        yum install -y curl >> "${BUILD_LOG}" 2>&1
      else
        yum check-update || true
        yum install -y curl
      fi
    elif command -v dnf >/dev/null 2>&1; then
      if [[ "${QUIET}" == "1" ]]; then
        dnf -y install curl >> "${BUILD_LOG}" 2>&1
      else
        dnf -y install curl
      fi
    elif command -v apk >/dev/null 2>&1; then
      if [[ "${QUIET}" == "1" ]]; then
        apk add --no-cache curl >> "${BUILD_LOG}" 2>&1
      else
        apk add --no-cache curl
      fi
    else
      echo "No supported package manager found to install curl"
      exit 1
    fi
  fi

  # CMAKE
  cd "${ROOT}"
  if [[ "${QUIET}" == "1" ]]; then
    curl -sSLo cmake-3.31.0.tar.gz https://cmake.org/files/v3.31/cmake-3.31.0.tar.gz >> "${BUILD_LOG}" 2>&1
    tar -xzf cmake-3.31.0.tar.gz >> "${BUILD_LOG}" 2>&1
  else
    curl -O https://cmake.org/files/v3.31/cmake-3.31.0.tar.gz
    tar -xzvf cmake-3.31.0.tar.gz
  fi
  cd cmake-3.31.0
  if [[ "${QUIET}" == "1" ]]; then
    ./bootstrap -- -DCMAKE_USE_OPENSSL=OFF >> "${BUILD_LOG}" 2>&1
    make -j2 >> "${BUILD_LOG}" 2>&1
    make install >> "${BUILD_LOG}" 2>&1
  else
    ./bootstrap -- -DCMAKE_USE_OPENSSL=OFF
    make -j2
    make install
  fi
  cmake --version

  # LightGBM
  cd "${DEPS_DIR}"
  rm -rf LightGBM
  if [[ "${QUIET}" == "1" ]]; then
    git clone --recursive https://github.com/microsoft/LightGBM >> "${BUILD_LOG}" 2>&1
  else
    git clone --recursive https://github.com/microsoft/LightGBM
  fi
  cd LightGBM
  mkdir -p build
  cd build
  if [[ "${QUIET}" == "1" ]]; then
    cmake -DBUILD_STATIC_LIB=ON -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DUSE_OPENMP=OFF .. >> "${BUILD_LOG}" 2>&1
    make -j4 >> "${BUILD_LOG}" 2>&1
  else
    cmake -DBUILD_STATIC_LIB=ON -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DUSE_OPENMP=OFF ..
    make -j4
  fi
  cd ..
  cp lib_lightgbm.a "${LGBM_LIB}"

  # FFTW
  cd "${DEPS_DIR}"
  rm -rf fftw-3.3.10 fftw-3.3.10.tar.gz
  if [[ "${QUIET}" == "1" ]]; then
    curl -sSLo fftw-3.3.10.tar.gz https://www.fftw.org/fftw-3.3.10.tar.gz >> "${BUILD_LOG}" 2>&1
    tar -xzf fftw-3.3.10.tar.gz >> "${BUILD_LOG}" 2>&1
  else
    curl -O https://www.fftw.org/fftw-3.3.10.tar.gz
    tar -xzvf fftw-3.3.10.tar.gz
  fi
  cd fftw-3.3.10
  if [[ "${QUIET}" == "1" ]]; then
    ./configure --with-pic >> "${BUILD_LOG}" 2>&1
    make -j4 CFLAGS=-fPIC >> "${BUILD_LOG}" 2>&1
    make install >> "${BUILD_LOG}" 2>&1
  else
    ./configure --with-pic
    make -j4 CFLAGS=-fPIC
    make install
    ls -l .libs/
  fi
  cp .libs/libfftw3.a "${FFTW_LIB}"
  cp api/fftw3.h "${FFTW_HDR}"

  restore_fftw
  restore_lgbm
fi

# luna-base (built in all/luna modes)
cd "${DEPS_DIR}"
rm -rf luna-base
if [[ "${QUIET}" == "1" ]]; then
  git clone https://github.com/remnrem/luna-base.git >> "${BUILD_LOG}" 2>&1
else
  git clone https://github.com/remnrem/luna-base.git
fi
cd luna-base
if [[ "${QUIET}" == "1" ]]; then
  make -j4 \
    LGBM=1 \
    LGBM_PATH=../LightGBM/ \
    CPPFLAGS="${CPPFLAGS:-} -I${DEPS_DIR}/include" \
    LDFLAGS="${LDFLAGS:-} -L${DEPS_DIR} -L/usr/local/lib -pthread" \
    LDLIBS="${LDLIBS:-} -pthread" >> "${BUILD_LOG}" 2>&1 || {
    echo "luna-base build failed; tail of ${BUILD_LOG}:"
    tail -n 200 "${BUILD_LOG}" || true
    exit 1
  }
else
  make -j4 \
    LGBM=1 \
    LGBM_PATH=../LightGBM/ \
    CPPFLAGS="${CPPFLAGS:-} -I${DEPS_DIR}/include" \
    LDFLAGS="${LDFLAGS:-} -L${DEPS_DIR} -L/usr/local/lib -pthread" \
    LDLIBS="${LDLIBS:-} -pthread"
fi
cp libluna.a "${LUNA_LIB}"

restore_luna
save_cache_payload
