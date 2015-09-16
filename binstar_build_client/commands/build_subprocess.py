"""Run a build as a build user"""

from binstar_client.utils import get_binstar
from binstar_build_client import BinstarBuildAPI
from argparse import RawDescriptionHelpFormatter
import json
import pickle
import sys
from tempfile import NamedTemporaryFile
from binstar_build_client.worker.worker import Worker
import logging
import os
log = logging.getLogger('binstar.build')
def main(args):
    build_user, job_data, worker_self = pickle.load(open(args.pickled))
    os.remove(args.pickled)
    bs = get_binstar(args, cls=BinstarBuildAPI)
    worker = Worker(bs, worker_self['args'], [build_user])
    worker.__dict__.update(worker_self)
    build_results = json.dumps(worker.build(job_data))
    log.info('build results:\n' + build_results)
    f = NamedTemporaryFile(delete=False)
    f.write(build_results)
    f.close()
    sys.stdout.write('BUILD_RESULTS_FILE:%s' % f.name)
    
            

def add_parser(subparsers):
    parser = subparsers.add_parser('build_subprocess',
                                   description=__doc__,
                                   formatter_class=RawDescriptionHelpFormatter,
                                   )
    parser.add_argument('pickled')
    parser.set_defaults(main=main)
    return parser