#!/usr/bin/env bash
set -euo pipefail

cp CMakeLists.txt.MAC_x86 CMakeLists.txt

ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
DEPS_DIR="${ROOT}/depends"
CACHE_DIR="${DEPENDS_CACHE_DIR:-${ROOT}/depends-cache/macos}"
MODE="${NATIVE_DEPS_MODE:-lunapi}"
LIGHTGBM_REF="${LIGHTGBM_REF:-v4.6.0}"
ORT_REF="${ORT_REF:-v1.29.0}"

mkdir -p "${DEPS_DIR}" "${CACHE_DIR}"

FFTW_LIB="${CACHE_DIR}/libfftw3.a"
FFTW_HDR="${CACHE_DIR}/fftw3.h"
LGBM_LIB="${CACHE_DIR}/lib_lightgbm.a"
LUNA_LIB="${CACHE_DIR}/libluna.a"
LGBM_INCLUDE_CACHE="${CACHE_DIR}/LightGBM-include"
LUNA_BASE_CACHE="${CACHE_DIR}/luna-base"
DEPS_INCLUDE_CACHE="${CACHE_DIR}/include"
ORT_CACHE="${CACHE_DIR}/onnxruntime"
ORT_DIST="${DEPS_DIR}/onnxruntime"

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

have_ort_cache() {
  [[ -f "${ORT_CACHE}/lib/libonnxruntime.dylib" && -d "${ORT_CACHE}/include/onnxruntime" ]]
}

restore_fftw() {
  chmod u+w "${DEPS_DIR}/libfftw3.a" "${DEPS_DIR}/include/fftw3.h" 2>/dev/null || true
  cp "${FFTW_LIB}" "${DEPS_DIR}/libfftw3.a"
  mkdir -p "${DEPS_DIR}/include"
  cp "${FFTW_HDR}" "${DEPS_DIR}/include/fftw3.h"
}

restore_lgbm() {
  chmod -R u+w "${DEPS_DIR}/LightGBM" 2>/dev/null || true
  chmod u+w "${DEPS_DIR}/lib_lightgbm.a" 2>/dev/null || true
  cp "${LGBM_LIB}" "${DEPS_DIR}/lib_lightgbm.a"
  mkdir -p "${DEPS_DIR}/LightGBM"
  cp "${LGBM_LIB}" "${DEPS_DIR}/LightGBM/lib_lightgbm.a"
  mkdir -p "${DEPS_DIR}/LightGBM/lib"
  cp "${LGBM_LIB}" "${DEPS_DIR}/LightGBM/lib/lib_lightgbm.a"
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
  chmod -R u+w "${DEPS_DIR}/luna-base" 2>/dev/null || true
  chmod u+w "${DEPS_DIR}/libluna.a" 2>/dev/null || true
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

restore_ort() {
  rm -rf "${ORT_DIST}"
  cp -R "${ORT_CACHE}" "${ORT_DIST}"
}

save_cache_payload() {
  rm -rf "${LGBM_INCLUDE_CACHE}" "${LUNA_BASE_CACHE}" "${DEPS_INCLUDE_CACHE}" "${ORT_CACHE}"
  cp -R "${DEPS_DIR}/LightGBM/include" "${LGBM_INCLUDE_CACHE}"
  cp -R "${DEPS_DIR}/luna-base" "${LUNA_BASE_CACHE}"
  if [[ -d "${DEPS_DIR}/include" ]]; then
    cp -R "${DEPS_DIR}/include" "${DEPS_INCLUDE_CACHE}"
  fi
  cp -R "${ORT_DIST}" "${ORT_CACHE}"
  echo "CACHE_DIR=${CACHE_DIR}"
  ls -la "${CACHE_DIR}"
  ls -la "${DEPS_DIR}" || true
}

if [[ "${MODE}" == "lunapi" ]]; then
  if ! have_fftw_cache || ! have_lgbm_cache || ! have_luna_cache || ! have_ort_cache; then
    echo "lunapi mode requires cached FFTW/LGBM/luna-base/onnxruntime artifacts, but cache is incomplete"
    echo "have_fftw_cache=$(have_fftw_cache && echo true || echo false)"
    echo "have_lgbm_cache=$(have_lgbm_cache && echo true || echo false)"
    echo "have_luna_cache=$(have_luna_cache && echo true || echo false)"
    echo "have_ort_cache=$(have_ort_cache && echo true || echo false)"
    exit 1
  fi
  echo "Using cached native dependencies from ${CACHE_DIR} (lunapi-only mode)"
  restore_fftw
  restore_lgbm
  restore_luna
  restore_ort
  restore_optional_dep_include
  echo "CACHE_DIR=${CACHE_DIR}"
  ls -la "${CACHE_DIR}"
  ls -la "${DEPS_DIR}" || true
  exit 0
fi

if [[ "${MODE}" == "luna" ]]; then
  if ! have_fftw_cache || ! have_lgbm_cache || ! have_ort_cache; then
    echo "luna mode requires cached FFTW/LGBM/onnxruntime artifacts, but cache is incomplete"
    echo "have_fftw_cache=$(have_fftw_cache && echo true || echo false)"
    echo "have_lgbm_cache=$(have_lgbm_cache && echo true || echo false)"
    echo "have_ort_cache=$(have_ort_cache && echo true || echo false)"
    exit 1
  fi
  echo "Using cached FFTW/LGBM and rebuilding luna-base"
  restore_fftw
  restore_lgbm
  restore_optional_dep_include
  restore_ort
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
  cp .libs/libfftw3.a "${FFTW_LIB}"
  cp api/fftw3.h "${FFTW_HDR}"
  restore_fftw

  # LightGBM
  cd "${DEPS_DIR}"
  rm -rf LightGBM
  git clone --recursive --branch "${LIGHTGBM_REF}" --depth 1 https://github.com/microsoft/LightGBM
  cd LightGBM
  mkdir -p build
  cd build
  cmake -DBUILD_STATIC_LIB=ON -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DUSE_OPENMP=OFF ..
  make -j4
  cp ../lib_lightgbm.a "${LGBM_LIB}"
  cp ../lib_lightgbm.a "${DEPS_DIR}/lib_lightgbm.a"
  mkdir -p "${DEPS_DIR}/LightGBM/lib"
  cp ../lib_lightgbm.a "${DEPS_DIR}/LightGBM/lib/lib_lightgbm.a"

  # ONNX Runtime: shared, CPU-only, with contrib/ML operators and telemetry off.
  cd "${DEPS_DIR}"
  rm -rf onnxruntime-src
  git clone --branch "${ORT_REF}" --depth 1 \
    https://github.com/microsoft/onnxruntime onnxruntime-src
  cd onnxruntime-src
  python3 tools/ci_build/build.py \
    --build_dir build/MacOS/ReleaseShared \
    --config Release \
    --build_shared_lib \
    --skip_tests \
    --parallel 0 \
    --disable_contrib_ops \
    --disable_ml_ops \
    --no_telemetry \
    --cmake_extra_defines onnxruntime_BUILD_UNIT_TESTS=OFF \
    --target onnxruntime \
    --cmake_generator "Unix Makefiles" \
    --update \
    --build
  rm -rf "${ORT_DIST}"
  mkdir -p "${ORT_DIST}/lib" "${ORT_DIST}/include"
  cp build/MacOS/ReleaseShared/Release/libonnxruntime.dylib "${ORT_DIST}/lib/"
  cp -R include/onnxruntime "${ORT_DIST}/include/"
  install_name_tool -id '@rpath/libonnxruntime.dylib' \
    "${ORT_DIST}/lib/libonnxruntime.dylib"
fi

# luna-base (built in all/luna modes)
cd "${DEPS_DIR}"
rm -rf luna-base
git clone https://github.com/remnrem/luna-base.git
cd luna-base
make -j4 ARCH=MAC LGBM=1 LGBM_PATH=../LightGBM/ \
  CPPFLAGS="${CPPFLAGS:-} -I${DEPS_DIR}/include" \
  ORT=1 ORT_PATH="${ORT_DIST}"
cp libluna.a "${LUNA_LIB}"
restore_luna

save_cache_payload
exit 0
