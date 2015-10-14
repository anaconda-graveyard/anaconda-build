from binstar_build_client.worker_commands.deregister import main as deregister_main
from binstar_build_client.worker_commands.deregister import add_parser as dereg_add_parser

def main(args):
    return deregister_main(args, context="docker_worker")

def add_parser(subparsers, name='deregister',
               description='Deregister a build worker to build jobs off of a binstar build queue',
               epilog=__doc__):
    return dereg_add_parser(subparsers, name,
                          description, epilog, default_func=main)