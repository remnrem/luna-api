
cp CMakeLists.txt.GITHUB CMakeLists.txt

cd ${GITHUB_WORKSPACE}
mkdir ${GITHUB_WORKSPACE}/depends


cmake --version

yum check-update
yum install -y cmake
    #|| apk add --upgrade cmake || apt-get install cmake

cmake --version

#Programs and libraries are not installed on the CI runner host, but
# rather should be installed inside the container - using yum for
# manylinux2010 or manylinux2014, apt-get for manylinux_2_24, dnf for
# manylinux_2_28 and apk for musllinux_1_1 or musllinux_1_2, or
# manually. The same goes for environment variables that are
# potentially needed to customize# the wheel building.

#cibuildwheel supports this by providing the CIBW_ENVIRONMENT and
#CIBW_BEFORE_ALL options to setup the build environment inside the
#run#ning container.


# CMAKE
#curl -O https://cmake.org/files/LatestRelease/cmake-3.31.0.tar.gz
#tar -xzvf cmake-3.31.0.tar.gz
#cd cmake-3.31.0
#./bootstrap -- -DCMAKE_USE_OPENSSL=OFF
#make -j2
#make install

# LightGBM
cd ${GITHUB_WORKSPACE}/depends/
git clone --recursive https://github.com/microsoft/LightGBM
cd LightGBM
mkdir build
cd build
cmake -DBUILD_STATIC_LIB=ON  -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DUSE_OPENMP=OFF ..
make -j4
cd ..
cp lib_lightgbm.a ${GITHUB_WORKSPACE}/depends/

# FFTW
cd ${GITHUB_WORKSPACE}/depends/
curl -O https://www.fftw.org/fftw-3.3.10.tar.gz
tar -xzvf fftw-3.3.10.tar.gz 
cd fftw-3.3.10
./configure --with-pic
make -j4 CFLAGS=-fPIC
make install
ls -l .libs/
cp .libs/libfftw3.a ${GITHUB_WORKSPACE}/depends/


# luna-base
cd ${GITHUB_WORKSPACE}/depends/
git clone https://github.com/remnrem/luna-base.git
cd luna-base
make -j4 ARCH=MAC LGBM=1 LGBM_PATH=../LightGBM/
cp libluna.a ${GITHUB_WORKSPACE}/depends/

ls -l ${GITHUB_WORKSPACE}/depends

