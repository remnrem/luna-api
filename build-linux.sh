
cp CMakeLists.txt.GITHUB CMakeLists.txt

cd ${GITHUB_WORKSPACE}
mkdir depends

cd ${GITHUB_WORKSPACE}/depends

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
cp lib_lightgbm.a /depends/

# luna-base
cd ${GITHUB_WORKSPACE}/depends/
git clone https://github.com/remnrem/luna-base.git
cd luna-base
make -j4 ARCH=MAC LGBM=1 LGBM_PATH=../LightGBM/
cp libluna.a ${GITHUB_WORKSPACE}/depends/

ls -l ${GITHUB_WORKSPACE}/depends

