

import os

CONDA_EXE = 'conda.exe' if os.name == 'nt' else 'conda'

def get_conda_root_prefix():

    for entry in os.environ.get('PATH').split(os.pathsep):

        if os.path.isdir(entry) and CONDA_EXE in os.listdir(entry):
            conda_exe_path = os.path.realpath(os.path.join(entry, 'conda'))
            bin_dir = os.path.dirname(conda_exe_path)
            return os.path.dirname(bin_dir)

