'''
Created on May 8, 2014

@author: sean
'''


from __future__ import (print_function, unicode_literals, division,
    absolute_import)

from itertools import product

def expand_build_matrix(instruction_set):
    instruction_set = instruction_set.copy()

    platforms = instruction_set.pop('platform', ['linux-64']) or [None]
    if not isinstance(platforms, list): platforms = [platforms]
    envs = instruction_set.pop('env', [None]) or [None]
    if not isinstance(envs, list): envs = [envs]
    engines = instruction_set.pop('engine', ['python=2']) or [None]
    if not isinstance(engines, list): engines = [engines]

    for platform, env, engine in product(platforms, envs, engines):
        build = instruction_set.copy()
        build.update(platform=platform, env=env, engine=engine)
        yield build

def serialize_builds(instruction_sets):
    builds = {}
    for instruction_set in instruction_sets:
        for build in expand_build_matrix(instruction_set):
            k = '%s::%s::%s' % (build['platform'], build['engine'], build['env'])
            bld = builds.setdefault(k, build)
            bld.update(build)

    for k, value in sorted(builds.items()):
        if value.get('exclude'): continue
        yield value
