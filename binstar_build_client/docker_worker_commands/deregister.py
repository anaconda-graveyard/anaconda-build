from functools import partial

from binstar_build_client.worker.register import deregister_worker_main
from binstar_build_client.worker_commands.deregister import add_parser as add_parser_dereg

def main(args):
    return deregister_worker_main(args, context="docker_worker")

add_parser = partial(add_parser_dereg, default_func=main)