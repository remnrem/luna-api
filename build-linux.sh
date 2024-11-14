
cp CMakeLists.txt.GITHUB CMakeLists.txt

cd ${GITHUB_WORKSPACE}
mkdir ${GITHUB_WORKSPACE}/depends

cd ${GITHUB_WORKSPACE}/depends

# CMAKE
sudo apt update
sudo apt install -y wget
wget https://cmake.org/files/v3.8/cmake-3.8.2.tar.gz
tar -zxvf cmake-3.8.2.tar.gz
cd cmake-3.8.2
./bootstrap
make -j$(nproc)
make install

# FFTW
curl -O https://www.fftw.org/fftw-3.3.10.tar.gz
tar -xzvf fftw-3.3.10.tar.gz 
cd fftw-3.3.10
./configure --with-pic
make -j4 CFLAGS=-fPIC
make install
ls -l .libs/
cp .libs/libfftw3.a ${GITHUB_WORKSPACE}/depends/

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

# luna-base
cd ${GITHUB_WORKSPACE}/depends/
git clone https://github.com/remnrem/luna-base.git
cd luna-base
make -j4 ARCH=MAC LGBM=1 LGBM_PATH=../LightGBM/
cp libluna.a ${GITHUB_WORKSPACE}/depends/

ls -l ${GITHUB_WORKSPACE}/depends

