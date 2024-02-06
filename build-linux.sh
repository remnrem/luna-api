
#sudo apt-get update
#sudo apt-get -y install wget libomp-dev

cd ${GITHUB_WORKSPACE}

cp CMakeLists.txt.LINUX CMakeLists.txt

mkdir /depends
cd /depends

# FFTW
curl -O https://www.fftw.org/fftw-3.3.10.tar.gz
tar -xzvf fftw-3.3.10.tar.gz 
cd fftw-3.3.10
./configure --with-pic
make -j4 CFLAGS=-fPIC
make install
ls -l .libs/
cp .libs/libfftw3.a /depends/

# LightGBM
cd /depends/
git clone --recursive https://github.com/microsoft/LightGBM
cd LightGBM
mkdir build
cd build
cmake -DBUILD_STATIC_LIB=ON  -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DUSE_OPENMP=OFF ..
make -j4
cd ..
cp lib_lightgbm.a /depends/

# luna-base
cd /depends/
git clone https://github.com/remnrem/luna-base.git
cd luna-base
make -j4 ARCH=MAC LGBM=1 LGBM_PATH=../LightGBM/
cp libluna.a /depends/

ls -l /depends

