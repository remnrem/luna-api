
cd ${GITHUB_WORKSPACE}

mkdir depends
# get libs
wget -O macos-arm64.tar.gz "https://www.dropbox.com/scl/fi/72zja7ykxvc604zwi3ukd/macos-arm64.tar.gz?rlkey=ndoxbrmddmkxirz42twrwkcvi&dl=0"
tar xzvf macos-arm64.tar.gz
cp macos-arm64/*.a depends/

brew install fftw

pwd

ls -l

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

ls -l
echo "here"
ls -lR
