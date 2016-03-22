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

### Login

` $ anaconda login`

Test your login with the whoami command:

` $ anaconda whoami`

For a complete tutorial on building and uploading Conda packages to Anaconda Cloud read the [Getting Started Guide](http://docs.anaconda.org/quickstart.html#BuildAndUploadPackages).

For detailed information on registering Workers with Anaconda Build Queues read the [Build Reference](http://docs.anaconda.org/build.html).

## Installing from source

run 

```bash
git clone https://github.com/Anaconda-Server/anaconda-build
cd anaconda-build
python setup.py [develop|install]
```

Here is an example of informally testing anaconda-build that can be run after installing prerequisite packages, such as Visual Studio, Apple Developer Tools, and git.

Make sure build-related Python packages are up-to-date
```
conda update -n root conda-build conda
conda create -n build_env python=2.7 anaconda-build chalmers anaconda-client ndg-httpsclient jinja2 mock
source activate build_env
```
Login and come up with a queue name (user/queue)
```
# login to anaconda
anaconda login

# Make an env variable for your anaconda.org username, for me that is
export anaconda_user=psteinberg
export queue=${anaconda_user}/abc
```
create a build queue if you don't have one in your account yet
```
anaconda build queue --create ${queue}
```
Register a worker, adjusting the worker name, distribution and platform as necessary
```
export WORKER_ID=worker_1
anaconda worker register ${queue} --dist darwin --platform osx-64 --name ${WORKER_ID}

```
Run a worker list command to check registered workers
```
anaconda worker list
```
Create an anaconda.org auth token so worker can be run while you are not logged in
```
anaconda auth --create -n "anaconda-build-OSX-64" --scopes "api:build-worker" --out ~/.anaconda.token
```
Logout
```
anaconda logout
```
Add a chalmers managed program for the worker
```
chalmers add --name worker -c "anaconda --show-traceback -t ${HOME}/.anaconda.token worker run ${WORKER_ID} --status-file" ${HOME}/.worker.status
```
Start chalmers
```
# Start chalmers with streaming output (--all can be replaced by "worker" in this case)

chalmers start --all --stream -w
```
Leave that running, open a separate tab and submit a build to your queue
```
# First make an env var for your queue, for me that is
export queue=psteinberg/abc # username/queuename
# Submit a local package directory with a .binstar.yml,
# using the `--platform` filter to only include the build/test entries
# relevant to this platform.

anaconda build submit ./path/to/package --queue ${queue} --platform osx-64

# Then watch the output for the builds you can tail, with something like
anaconda build tail -f username/packagename 1.0 

# Alternatively trigger a build for a github repo
# that has CI enabled.  Find CI options for your package at a url
# like: https://anaconda.org/psteinberg/astropy/settings/ci ,
# replacing psteinberg and astropy with your username and package name.
# Triggering uses your anaconda.org username/packagename with arguments,
# again limiting the builds from the .binstar.yml in the github repo
# to those on this platform
anaconda build trigger psteinberg/myorg.package1 --queue ${queue} --platform osx-64

# optionally tail the results or view them at anaconda.org
```
