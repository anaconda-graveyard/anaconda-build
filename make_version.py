from subprocess import check_output
import os

def git_describe():
    output = check_output(['git', 'describe', '--always', '--long']).strip().split('-')
    if len(output) == 3:
        version, build, commit = output
    else:
        raise Exception("Could not git describe, (got %s)" % output)

    print("Version: %s" % version)
    print("Build: %s" % build)
    print("Commit: %s" % commit)
    return  version, build, commit

def pypi_version():
    version, build, _ = git_describe()
    return "%s.post%s" % (version, build)

def write_pypi_version(package, version, build, commit):
    print("Writing %s/_version.py" % package)
    with open('%s/_version.py' % package, 'w') as fd:
        if build == '0':
            fd.write('__version__ = "%s"\n' % (version))
        else:
            fd.write('__version__ = "%s.post%s"\n' % (version, build))
        fd.write('__commit__ = "%s"\n' % (commit))

def write_conda_version(version, build, commit):
    SRC_DIR = os.environ.get('SRC_DIR', '.')

    conda_version_path = os.path.join(SRC_DIR, '__conda_version__.txt')
    print("Writing %s" % conda_version_path)
    with open(conda_version_path, 'w') as conda_version:
        conda_version.write(version)

    conda_buildnum_path = os.path.join(SRC_DIR, '__conda_buildnum__.txt')
    print("Writing %s" % conda_buildnum_path)

    with open(conda_buildnum_path, 'w') as conda_buildnum:
        conda_buildnum.write(build)

def main():
    version, build, commit = git_describe()

    write_pypi_version('binstar_build_client', version, build, commit)
    write_conda_version(version, build, commit)


if __name__ == '__main__':
    main()
