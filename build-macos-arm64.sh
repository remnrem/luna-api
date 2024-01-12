
mkdir depends
# get libs
wget -O macos-arm64.tar.gz "https://www.dropbox.com/scl/fi/7pii8r7hfkvtr8ufr0spa/macos-arm64.tar.gz?rlkey=6je0i913hk613x0fjx81ibwxm&dl=0"
tar xzvf macos-arm64.tar.gz
cp macos-arm64/*.a depends/

brew install fftw

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
