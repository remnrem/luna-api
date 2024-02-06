
mkdir /depends
cd /depends

# get libs: 
wget -O macos-arm64.tar.gz "https://www.dropbox.com/scl/fi/5fe5tcbo7zvz5f1vrmtw9/macos-arm64.tar.gz?rlkey=ncn72rme3sami0dk538uhu52x&dl=0"
tar xzvf macos-arm64.tar.gz
cp macos-arm64/*.a /depends/

brew install fftw

pwd

ls -l

cd /depends

# includes only
# FFTW
wget https://www.fftw.org/fftw-3.3.10.tar.gz
tar -xzvf fftw-3.3.10.tar.gz 

# LightGBM
cd /depends/
git clone --recursive https://github.com/microsoft/LightGBM

# luna-base
cd /depends/
git clone https://github.com/remnrem/luna-base.git
cp libluna.a luna-base/

cd /depends
ls -l

