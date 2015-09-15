"""
anaconda build register-worker <username> 

Registers a worker under a username.  The user's proceses
are killed and a clean build/test environment is set up.
"""
import logging
import psutil
import io
import platform
import os
import sys
import time
from binstar_build_client import BinstarBuildAPI
from binstar_client.utils import get_binstar
from ..worker.utils.buffered_io import BufferedPopen
import subprocess as sp
from worker import get_platform, get_dist, get_conda_root_prefix
from binstar_client.errors import BinstarError
log = logging.getLogger('binstar.build')
STATE_FILE = 'worker.yaml'



def clean_home_dir(args):
    user_host = '%s@%s' % (args.ssh_user, args.hostname)
    home_dir = os.path.join(os.path.dirname(os.path.expanduser("~")), args.ssh_user)
    os.remove(home_dir)
    shutil.copytree('/etc/worker-skel', home_dir, symlinks=False)
    

def main(args):
    binstar = get_binstar(args, cls=BinstarBuildAPI)
    if os.path.isfile(STATE_FILE):
        with open(STATE_FILE, 'r') as fd:
            worker_data = yaml.load(fd)

        self.bs.remove_worker(self.args.username, self.args.queue, worker_data['worker_id'])
        log.info("Un-registered worker %s from binstar site" % worker_data['worker_id'])
        os.unlink(STATE_FILE)
        log.info("Removed worker.yaml")

    worker_id = binstar.register_worker(args.username, args.queue, args.platform,
                                        args.hostname, args.dist)
    
    log.info('New worker_id:\t%s' % worker_id)
    
    user_host = "%s@%s" % (args.ssh_user, args.hostname)
    config_url = sp.Popen(['anaconda', 'config', '--get', 'url'], 
                        stdin=sp.PIPE, 
                        stdout=sp.PIPE, 
                        stderr=sp.PIPE).communicate()[0].strip()
    worker_args = ['ssh',]
    if args.ssh_key_file:
        worker_args.extend(('-i', args.ssh_key_file))
    worker_args.append(user_host)
    ssh_str = " ".join(worker_args)
    not_passed = ('--start_worker','--ssh_key_file')
    extra_args1 = [args.username, '%s/%s' % (args.username, args.queue,), worker_id ]
    reg_idx = sys.argv.index('register')
    extra_args1.extend(sys.argv[idx] for idx in range(reg_idx + 5, len(sys.argv))
                        if not sys.argv[idx] and not (idx > 1 and sys.argv[idx-1] == 'ssh_key_file'))
    worker_args.append(' anaconda config --set url %s &&' % config_url +\
                       ' conda config --set always_yes true &&' +\
                       ' anaconda --token %s build worker ' % args.token_file +\
                       " ".join(extra_args1) 
                       )
    worker_proc = None
    start_str = '%s "%s"' % (ssh_str, worker_args[-1])
    bash_start_worker = 'start_worker_%s.sh' % worker_id
    kill_all_user_procs = ssh_str + ' "pkill -U %s"\n' % args.ssh_user
    with open(bash_start_worker, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write(kill_all_user_procs)
        f.write(start_str)
        log.info('Wrote worker start script to %s' % bash_start_worker)

    if not args.start_worker:
        log.info("Start the worker with " + start_str)
    else:
        log.info("Kill all processes by %s" % user_host)
        out, err = sp.Popen(['ssh', user_host, "pkill -U %s" % args.ssh_user],
              stdout=sp.PIPE, stderr=sp.PIPE, stdin=sp.PIPE).communicate()
        log.info(out)
        log.info(err)
        log.info('Starting the worker with: '+ start_str)
        clean_home_dir(args)        
        try:
            worker_proc = sp.Popen(worker_args, stdout=sp.PIPE, stdin=sp.PIPE, stderr=sp.PIPE)
            exit_code = worker_proc.poll()
            while exit_code is None:
                line = 'x'
                while line != '':
                    line = worker_proc.stdout.readline()
                    if line:
                        log.info(line.rstrip())
                line = 'x'
                while line != '':
                    line = worker_proc.stderr.readline()
                    if line:
                        log.info(line.rstrip())
                exit_code = worker_proc.poll()
                time.sleep(.1)                
        except BaseException as e:
            log.error("Binstar build process caught an exception while waiting for the build to finish")
            raise
        finally:   
            log.info(worker_proc.stdout.read())
            log.info(worker_proc.stderr.read())
            log.info('Worker exit with worker_id:%r,username:%r' % (worker_id, args.username))
            binstar.remove_worker(args.username, args.queue, worker_id)

def add_parser(subparsers, name='register',
               description='TESTING REMOVE THIS TODO...Run a build worker to build jobs off of a binstar build queue',
               epilog=__doc__):

    parser = subparsers.add_parser(name,
                                   help=description, description=description,
                                   epilog=epilog
                                   )

    conda_platform = get_platform()
    parser.add_argument('ssh_user',
                        help='The queue to pull builds from')

    parser.add_argument('username', help="Anaconda server user name.")
    parser.add_argument('queue', metavar='OWNER/QUEUE',
                        help='The queue to pull builds from')
    parser.add_argument('token_file', help="Token file")
    parser.add_argument('--ssh_key_file', help="SSH public key file for authentication of workers")
    parser.add_argument("--start_worker",
                        action="store_true", 
                        help="Start the worker after registering it")
    parser.add_argument('-p', '--platform',
                        default=conda_platform,
                        help='The platform this worker is running on (default: %(default)s)')
    parser.add_argument('--hostname', default=platform.node(),
                        help='The host name the worker should use (default: %(default)s)')

    parser.add_argument('--dist', default=get_dist(),
                        help='The operating system distribution the worker should use (default: %(default)s)')

    parser.add_argument('--cwd', default='.',
                        help='The root directory this build should use (default: "%(default)s")')
    parser.add_argument('-t', '--max-job-duration', type=int, metavar='SECONDS',
                        dest='timeout',
                        help='Force jobs to stop after they exceed duration (default: %(default)s)', default=60 * 60 * 60)

    dgroup = parser.add_argument_group('development options')

    dgroup.add_argument("--conda-build-dir",
                        default=os.path.join(get_conda_root_prefix(), 'conda-bld', '{args.platform}'),
                        help="[Advanced] The conda build directory (default: %(default)s)",
                        )
    dgroup.add_argument('--show-new-procs', action='store_true', dest='show_new_procs',
                        help='Print any process that started during the build '
                             'and is still running after the build finished')

    dgroup.add_argument('-c', '--clean', action='store_true',
                        help='Clean up an existing workers session')
    dgroup.add_argument('-f', '--fail', action='store_true',
                        help='Exit main loop on any un-handled exception')
    dgroup.add_argument('-1', '--one', action='store_true',
                        help='Exit main loop after only one build')
    dgroup.add_argument('--push-back', action='store_true',
                        help='Developers only, always push the build *back* onto the build queue')

    dgroup.add_argument('--status-file',
                        help='If given, binstar will update this file with the time it last checked the anaconda server for updates')

    parser.set_defaults(main=main)


    return parser

