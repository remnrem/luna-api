
mkdir depends
# get libs
wget -O macos-arm64.tar.gz "https://www.dropbox.com/scl/fi/zg2itwsoc8bo0018w969n/macos-arm64.tar.gz?rlkey=3lj8v9ziig9fggs8fz928d80a&dl=0"
tar xzvf macos-arm64.tar.gz
cp macos-arm64/*.a depends/

cd depends

# includes only
# FFTW
wget https://www.fftw.org/fftw-3.3.10.tar.gz
tar -xzvf fftw-3.3.10.tar.gz 

# LightGBM
git clone --recursive https://github.com/microsoft/LightGBM

# luna-base
git clone https://github.com/remnrem/luna-base.git
cp libluna.a luna-base/
cd ..
