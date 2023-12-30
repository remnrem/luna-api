# luna-api

Luna API &amp; Python bindings

## Working notes

Assumptions:

 - luna is installed and `libluna.so` is a system library folder (e.g. on Linux, with `sudo` privileges `cp` to `/usr/local/lib` and then `ldconfig`) 

 - LightGBM, FFTW and zlib are similarly available system-wide

 - modify `-L` paths below or add `-Wl,-rpath` etc as needed
 

### C/C++


```
g++ -O2 -std=gnu++17 example.cpp -o example -I../luna-base -lluna -lz -lfftw3 -l_lightgbm
```

Run, assuming `learn-nsrr01.edf` and `learn-nsrr01-profusion.xml` are in the current folder:

```
./example
```

### Python

To build the Python module for lunapi using pybind11

```
pip install pybind11
```

```
g++ -O3 -Wall -shared -std=c++17 -fPIC \
     -I../luna-base/ -I../luna-base/stats \
     $(python3 -m pybind11 --includes) \
     -Wno-sign-compare \
     `python3-config --ldflags` \
     lunapi.cpp \
     -o lunapi$(python3-config --extension-suffix) \
     -lluna -l_lightgbm -lfftw3 -lz
```

### Docker


```
docker build -t lunapi .
```

```
docker run -it --rm  --user root -e GRANT_SUDO=yes -p 8888:8888 -v "${PWD}":/home/jovyan/work quay.io/jupyter/datascience-notebook
```

```
docker run -it --rm -p 8888:8888 -v "${PWD}":/lunapi lunapi
```


### misc notes


```
pip install pybind11
```


```
g++ -O3 -Wall -shared -std=c++17 -fPIC      -I/build/luna-base/ -I/build/luna-base/stats      $(python3 -m pybind11 --includes)      -Wno-sign-compare      `python3-config --ldflags`      lunapi.cpp      -o lunapi$(python3-config --extension-suffix)      -lluna -l_lightgbm -lfftw3 -lz
```




