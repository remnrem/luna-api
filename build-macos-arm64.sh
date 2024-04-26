
# location of file 'macos-arm64.tar.gz' that should contain static libraries
# compiled on ARM64 for macOS:
#
#   libluna.a
#   lib_lightgbm.a
#   libfftw3.a
#
# (locally, these are stored on MGB dropbox share/luna-libs/macos-arm64.tar.gz)

BUNDLE="https://www.dropbox.com/scl/fi/dgia40biiyvw6i7t70jcj/macos-arm64.tar.gz?rlkey=pio8jutbqy2vqhcxpaxhjh2dn&dl=0"

cp CMakeLists.txt.GITHUB CMakeLists.txt

echo "ls"

ls -l

echo "pwd"
pwd

echo "GITHUB_WORKSPACE = "
echo ${GITHUB_WORKSPACE}

cd ${GITHUB_WORKSPACE}
mkdir depends

# get libs: 
wget -O macos-arm64.tar.gz ${BUNDLE}
tar xzvf macos-arm64.tar.gz
cp macos-arm64/*.a ${GITHUB_WORKSPACE}/depends/

#brew install fftw

pwd

ls -l

cd ${GITHUB_WORKSPACE}/depends

# includes only
# FFTW
wget https://www.fftw.org/fftw-3.3.10.tar.gz
tar -xzvf fftw-3.3.10.tar.gz 
cd fftw-3.3.10
./configure --prefix=${GITHUB_WORKSPACE}/depends/
make -j4
make install

# LightGBM
cd ${GITHUB_WORKSPACE}/depends/
git clone --recursive https://github.com/microsoft/LightGBM

# luna-base
cd ${GITHUB_WORKSPACE}/depends/
git clone https://github.com/remnrem/luna-base.git
cp libluna.a luna-base/

echo "Final"
cd ${GITHUB_WORKSPACE}

ls -l /Users/runner/work/luna-api/luna-api/depends/fftw-3.3.10/include

echo "Final"

ls -lR depends

#ls -l
#ls -l /Users/runner/work/luna-api/luna-api/
#ls -l /Users/runner/work/luna-api/luna-api/depends
#ls -l /Users/runner/work/luna-api/luna-api/depends/fftw-3.3.10
#ls -l /Users/runner/work/luna-api/luna-api/depends/fftw-3.3.10/include 
#ls -l /usr/local/include/
