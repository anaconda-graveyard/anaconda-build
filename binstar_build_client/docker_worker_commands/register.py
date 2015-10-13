
from functools import partial

from binstar_build_client.worker.register import register_worker_main
from binstar_build_client.worker_commands.register import add_parser as add_parser_reg

def main(args):
    return register_worker_main(args, context="docker_worker")

add_parser = partial(add_parser_reg, default_func=main)