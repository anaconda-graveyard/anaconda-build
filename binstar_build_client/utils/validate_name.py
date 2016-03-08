import re

from binstar_client import errors

PATTERN = '^[a-zA-Z]+[a-zA-Z\-_0-9]*$'

def is_valid_name(name):
    '''is_valid_name(name)
    Used to reject queue names like

    orgname/queue!
    orgname/que#e1
    orgname/_

    Params:
        name: the name to validate

    '''
    return bool(re.search(PATTERN, name))
