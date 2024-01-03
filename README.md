# luna-api

Luna API &amp; Python bindings

## Working notes

Assumptions:

 - _luna_ is installed and `libluna.so` is a system library folder
   (e.g. on Linux, with `sudo` privileges `cp` to `/usr/local/lib` and
   then running `ldconfig`);  on macOS copy `libluna.dylib` to `/usr/local/lib/` 

 - LightGBM, FFTW and zlib are similarly available system-wide

 - modify `-L` paths below or add `-Wl,-rpath` etc as needed
 

## C/C++

To test the set up, first compile a C/C++ program that uses _libluna_: 

```
g++ -O2 -std=gnu++17 example.cpp -o example -I../luna-base -lluna -lz -lfftw3 -l_lightgbm
```

Run, assuming `learn-nsrr01.edf` and `learn-nsrr01-profusion.xml` are in the current folder:

```
./example
```

and you should see the expected outputs.


## Building the Python library

To build the Python module for lunapi using pybind11

```
pip install pybind11
```

On Linux:
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

On macOS need to add `-undefined dynamic_lookup`:
```
g++ -O3 -Wall -shared -std=c++17 -fPIC \
     -I../luna-base/ -I../luna-base/stats \
     $(python3 -m pybind11 --includes) \
     -Wno-sign-compare \
     `python3-config --ldflags` \
     -undefined dynamic_lookup \
     lunapi.cpp \
     -o lunapi$(python3-config --extension-suffix) \
     -lluna -l_lightgbm -lfftw3 -lz
```

There will be an ignorable warning on macOS:
```
ld: warning: -undefined dynamic_lookup may not work with chained fixups
```

The above should generate a `.so` file that will be the imported module in python.

We also have some convenience helper functions in the Python text file `lunapy.py`


## Python

To test in Python:
```
import lunapi 
import lunapy as lp

help(lunapi)

p = lunapi.new( "id1" )

p.attach_edf( "learn-nsrr01.edf" )

p.attach_annot( "learn-nsrr01-profusion.xml" )

p

p.stat()

lp.stat(p)
```

Evaluating commands

```
p.eval( "HEADERS" )

p.commands()

p.strata()

p.table( 'HEADERS' , 'CH' ) 

p.tables()
```

Using the lunapy.py wrapper form:

```
lp.eval( p , "HEADERS" ) 

lp.strata(p)

lp.table( p, 'HEADERS' , 'CH' )
```

A variant form: `proc()` is `eval()` but also returns all outputs directly (as well as storing them
in the lunapi object
```
r = lp.proc( p , "HEADERS" )
```

### get data

```
d = p.data( chs = [ 'EEG' , 'EEG_sec' ] , annots = [] )

d

import matplotlib.pyplot as plt
plt.figure(figsize=(20,2))
plt.plot( d[1][1:1000:,0] , c = 'gray' , lw = 0.5 )
plt.show()
```

### get data by epoch, with annotations

```
p.e2i( range(5,10 ) )

d = p.slice( p.e2i( range(5,10 ) ) , chs = [ 'EEG' ] , annots = [ ] )

d = p.slices( p.e2i( range(5,10 ) ) , chs = [ 'EEG' ] , annots = [ ] )
```

## Docker

Based on the image:

```
https://jupyter-docker-stacks.readthedocs.io/en/latest/
```

i.e. running as is: (make sure port 8888 is not being used, e.g. by any local version of JuypterLab):

```
docker run -it --rm -p 8888:8888 -v "${PWD}":/home/jovyan/work quay.io/jupyter/datascience-notebook
```

To build the lunapi image:

```
docker build -t lunapi .
```

Then run:
```
docker run -it --rm -p 8888:8888 -v "${PWD}":/lunapi lunapi
```




