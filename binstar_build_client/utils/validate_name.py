import re

from binstar_client import errors

base_pattern = '^[a-zA-Z{}\-_0-9]+$'

def validate_name(n, context, allow_non_letters=''):
    if not allow_non_letters:
        allow_non_letters = ''
    pat = re.compile(base_pattern.format("".join(allow_non_letters)))
    if re.search(pat, n) is not None:
        pass
    else:
        raise errors.BinstarError('Invalid name for '
                                  '{}: {}'.format(context, n))
