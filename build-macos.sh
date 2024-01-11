
mkdir depends
cd depends

# FFTW
wget https://www.fftw.org/fftw-3.3.10.tar.gz
tar -xzvf fftw-3.3.10.tar.gz 
cd fftw-3.3.10
./configure
make -j4
make install
cp .libs/libfftw3.a ../
cd ..

# libomp
brew install libomp

# LightGBM
git clone --recursive https://github.com/microsoft/LightGBM
cd LightGBM
mkdir build
cd build
cmake -DBUILD_STATIC_LIB=ON ..
make -j4
cd ..
cp lib_lightgbm.a ../
cd ..

# luna-base
git clone https://github.com/remnrem/luna-base.git
cd luna-base
make -j4 LGBM=1 LGBM_PATH=../LightGBM/
cp libluna.a ../
cd ..
