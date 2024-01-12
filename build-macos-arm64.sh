mkdir depends
# get libs
wget -O macos-arm64.tar.gz "https://www.dropbox.com/scl/fi/zg2itwsoc8bo0018w969n/macos-arm64.tar.gz?rlkey=3lj8v9ziig9fggs8fz928d80a&dl=0"
tar xzvf macos-arm64.tar.gz
cp macos-arm64/*.a depends/

# luna-base include headers
cd depends
git clone https://github.com/remnrem/luna-base.git
cp libluna.a luna-base/
