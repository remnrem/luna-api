
cmake_minimum_required(VERSION 3.15...3.26)
project(${SKBUILD_PROJECT_NAME} LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_OSX_DEPLOYMENT_TARGET "10.14")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -I/usr/local/include -O2")
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -L/usr/local/lib -L/usr/local/opt/libomp/lib/")


set(PYBIND11_NEWPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)


#include_directories("/usr/local/include/")
include_directories("depends/fftw-3.3.10" "depends/fftw-3.3.10/include/" )
include_directories("depends/luna-base/" "depends/luna-base/stats")
include_directories("depends/LightGBM/include/")
include_directories("../luna-base/" "../luna-base/stats")
#include_directories("/opt/homebrew/include/")

link_directories("${CMAKE_CURRENT_SOURCE_DIR}/depends/")

add_library( luna STATIC IMPORTED GLOBAL )
add_library( lightgbm STATIC IMPORTED GLOBAL )
add_library( fftw3 STATIC IMPORTED GLOBAL )
#add_library( omp STATIC IMPORTED GLOBAL )

set_target_properties( luna      PROPERTIES IMPORTED_LOCATION "${CMAKE_CURRENT_SOURCE_DIR}/depends/libluna.a" )
set_target_properties( lightgbm   PROPERTIES IMPORTED_LOCATION "${CMAKE_CURRENT_SOURCE_DIR}/depends/lib_lightgbm.a" )
set_target_properties( fftw3     PROPERTIES IMPORTED_LOCATION "${CMAKE_CURRENT_SOURCE_DIR}/depends/libfftw3.a" )
#set_target_properties( omp     PROPERTIES IMPORTED_LOCATION "${CMAKE_CURRENT_SOURCE_DIR}/depends/libomp.a" )

pybind11_add_module( lunapi0 src/lunapi/lunapi0.cpp )

target_link_libraries( lunapi0 PRIVATE fftw3 luna lightgbm )

install(TARGETS lunapi0 LIBRARY DESTINATION lunapi )
