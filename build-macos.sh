
cp CMakeLists.txt.MAC_x86 CMakeLists.txt

cd ${GITHUB_WORKSPACE}
mkdir depends

# ensure (not present on macos-latest??)
sudo mkdir -p /usr/local/include
sudo mkdir -p /usr/local/bin
sudo mkdir -p /usr/local/lib


# FFTW
cd ${GITHUB_WORKSPACE}/depends
wget https://www.fftw.org/fftw-3.3.10.tar.gz
tar -xzvf fftw-3.3.10.tar.gz 
cd fftw-3.3.10
./configure --with-pic 
make -j4  CFLAGS=-fPIC
sudo make install

# LightGBM
cd ${GITHUB_WORKSPACE}/depends
git clone --recursive https://github.com/microsoft/LightGBM
cd LightGBM
mkdir build
cd build
cmake -DBUILD_STATIC_LIB=ON  -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DUSE_OPENMP=OFF ..
make -j4
sudo cp ../lib_lightgbm.a /usr/local/lib/

# luna-base
cd ${GITHUB_WORKSPACE}/depends
git clone https://github.com/remnrem/luna-base.git
cd luna-base
make -j4 ARCH=MAC LGBM=1 LGBM_PATH=../LightGBM/
sudo cp libluna.a /usr/local/lib/


ls -lrt /usr/local/lib
ls -lrt /usr/local/include
