if [ "$CONDA_NPY" == "" ];then
conda list | grep numpy && export CONDA_NPY=$(python -c "import sys;import numpy;sys.stdout.write(''.join(numpy.__version__.split('.')[:2]))") || export CONDA_NPY=""
fi
echo "CONDA_PY=$CONDA_PY"
echo "CONDA_NPY=$CONDA_NPY"