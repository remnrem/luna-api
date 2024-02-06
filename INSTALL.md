# Installation notes

## Docker

See notes at [https://github.com/remnrem/luna-api-notebooks](https://github.com/remnrem/luna-api-notebooks) for installing the Docker version of lunapi (based on a JupyterLab image).    This is currently the only option for Windows users.

## pip

We are aiming to support binary wheels for Linux and macOS (arm64 and
amd64).  If the following is able to find a matching binary wheel for
your platform, you can use that.

```
pip install lunapi 
```

## Manual build

We cannot currently provide support for manual builds - but if you
wish to follow these basic steps and have a working knowledge of
compiling software, this should work on Linux/macOS platforms.

 - follow the instructions [here](https://zzz.bwh.harvard.edu/luna/download/source/) for compiling Luna locally
 
 - this will involve obtaining the following two dependencies: FFTW3 and LightGBM libraries

 - download this repository; edit the CMakeLists.txt file to point to
   the location of Luna, FFTW and LightGBM headers and libraries; you
   may also need to make sure libomp/libgomp is available on your
   system

 - run `pip install .`

 - test in Python with `import lunapi as lp`


## Resources

The Docker image contains all resources (e.g. tutorial data, POPS
models, PREDICT models).  If you are building manually, or if you use
`pip` above, then you can obtain these resources from these locations;

 - notebook/tutorials : [https://github.com/remnrem/luna-api-notebooks](https://github.com/remnrem/luna-api-notebooks)

 - POPS models : `git clone https://gitlab.partners.org/zzz-public/nsrr.git`

 - PREDICT models : `git clone https://github.com/remnrem/moonlight/tree/main/models`

 - NSRR tutorial EDFs : `wget http://zzz.bwh.harvard.edu/dist/luna/tutorial.zip`

