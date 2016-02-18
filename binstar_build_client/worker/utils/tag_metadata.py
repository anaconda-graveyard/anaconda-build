
'''
Scan build logs for tags so Server UI knows what
tags are available.
'''
import os

from binstar_build_client.worker.utils.build_log import BuildLog

def list_build_log_section_tags():
    '''User'''
    tags = {'sh': set(), 'bat': set()}
    for end in ('sh', 'bat'):
        fname = os.path.join(os.path.dirname(__file__),
                         'data', 'build_script.' + end)
        with open(fname, 'r') as f:
            contents = f.readlines()
        for line in contents:
            if BuildLog.SECTION_TAG in line and not 'echo' in line:
                tag = [_.strip() for _ in line.strip().split(BuildLog.SECTION_TAG)]
                tag = " ".join([_ for _ in tag if not '%' in tag or '$' in tag])
                tags[end].add(tag)
    if not tags['sh'] == tags['bat']:
        raise ValueError('Expected same section tags for .sh and .bat'
                         ' build script templates. Got {}'.format(repr(tags)))

    return tags.pop('sh')

