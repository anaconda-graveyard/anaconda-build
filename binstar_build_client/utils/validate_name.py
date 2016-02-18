import re

from binstar_client import errors

base_pattern = '^[a-zA-Z{}\-_0-9]+$'

def validate_name(name, context, allow_non_letters=''):
    '''validate_name(name, context, allow_non_letters='')
    Used to reject queue names like

    orgname/queue!
    orgname/que#e1

    Params:
        name: the name to validate
        context: a context string for error messages if invalid
        allow_non_letters: iterable of characters

    raises BinstarError if name does not match regex
    of all letters / numbers, dash, underscore, plus the letters
    included in allow_non_letters.
    '''
    if not allow_non_letters:
        allow_non_letters = ''
    pat = re.compile(base_pattern.format("".join(allow_non_letters)))
    if re.search(pat, name) is not None:
        pass
    else:
        raise errors.BinstarError('Invalid name for '
                                  '{}: {}'.format(context, name))
