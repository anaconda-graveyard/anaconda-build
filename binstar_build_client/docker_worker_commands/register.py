from binstar_build_client.worker_commands.register import main as register_main
from binstar_build_client.worker_commands.register import add_parser as reg_add_parser

def main(args):
    return register_main(args, context="docker_worker")

def add_parser(subparsers, name='register',
               description='Register a build worker to build jobs off of a binstar build queue',
               epilog=__doc__):
    return reg_add_parser(subparsers, name,
                          description, epilog, default_func=main)