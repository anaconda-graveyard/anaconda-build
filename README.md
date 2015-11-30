Anaconda Build Client
=====================

This is a command line client that provides an interface to the [Anaconda Cloud](https://anaconda.org) build system.

## Quickstart:

### Create an account:

First create an account on [Anaconda Cloud](https://anaconda.org)

### Install the build client:

#### With Conda:

``` 
    $ conda install anaconda-build
```

#### Or pip:

```
   $ pip install anaconda-build
```

### Login


` $ anaconda login`

Test your login with the whoami command:

` $ anaconda whoami`

For a complete tutorial on building and uploading Conda packages to Anaconda Cloud read the [Getting Started Guide](http://docs.anaconda.org/quickstart.html#BuildAndUploadPackages).

For detailed information on registering Workers with Anaconda Build Queues read the [Build Reference](http://docs.anaconda.org/build.html).

## Installing from source

run 

```bash
git clone https://github.com/Binstar/binstar-build-client
cd binstar-build-client
python setup.py [develop|install]
```
