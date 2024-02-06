
echo "ls"

ls -l

echo "pwd"
pwd

echo "GITHUB_WORKSPACE = "
echo ${GITHUB_WORKSPACE}

cd ${GITHUB_WORKSPACE}

mkdir depends

# get libs: 
wget -O macos-arm64.tar.gz "https://www.dropbox.com/scl/fi/5fe5tcbo7zvz5f1vrmtw9/macos-arm64.tar.gz?rlkey=ncn72rme3sami0dk538uhu52x&dl=0"
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

# LightGBM
cd ${GITHUB_WORKSPACE}/depends/
git clone --recursive https://github.com/microsoft/LightGBM

# luna-base
cd ${GITHUB_WORKSPACE}/depends/
git clone https://github.com/remnrem/luna-base.git
cp libluna.a luna-base/

echo "Final"
cd ${GITHUB_WORKSPACE}
ls -l

echo "j1"
ls -l /Users/runner/work/luna-api/luna-api/depends/fftw-3.3.10
echo "j2"
ls -l /Users/runner/work/luna-api/luna-api/depends/fftw-3.3.10/include 

