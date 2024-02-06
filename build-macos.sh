
cd ${GITHUB_WORKSPACE}
mkdir depends

# FFTW
cd ${GITHUB_WORKSPACE}/depends
wget https://www.fftw.org/fftw-3.3.10.tar.gz
tar -xzvf fftw-3.3.10.tar.gz 
cd fftw-3.3.10
./configure --with-pic
make -j4  CFLAGS=-fPIC
make install

# LightGBM
cd ${GITHUB_WORKSPACE}/depends
git clone --recursive https://github.com/microsoft/LightGBM
cd LightGBM
mkdir build
cd build
cmake -DBUILD_STATIC_LIB=ON  -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DUSE_OPENMP=OFF ..
make -j4

# luna-base
cd ${GITHUB_WORKSPACE}/depends
git clone https://github.com/remnrem/luna-base.git
cd luna-base
make -j4 ARCH=MAC LGBM=1 LGBM_PATH=../LightGBM/
cp libluna.a /usr/local/lib/


ls -lrt /usr/local/lib
