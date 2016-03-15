from __future__ import unicode_literals, print_function, absolute_import
import io


class GeneratorFile(io.RawIOBase):
    '''
    A file-like object to wrap a generator that yields bytes
    '''

    def __init__(self, generator):
        self.generator = generator
        self.buffer = None

    def readable(self):
        return True

    def readinto(self, b):
        '''
        Read at most `len(b)` bytes into the buffer object `b`

        Args:
            b: The buffer to read

        Returns:
            The number of bytes read
        '''
        if self.buffer:
            # We still have some data left over from the last iteration, consume that
            data, self.buffer = self.buffer, None
        else:
            # Fetch some more data.
            data = next(self.generator, b'')

        bufsize = len(b)
        n = len(data)
        if n > bufsize:
            # We can only output bufsize bytes at a time, save the rest for later
            n = bufsize
            data, self.buffer = data[:n], data[n:]

        # See: https://github.com/python/cpython/blob/2.7/Lib/_pyio.py#L641
        try:
            b[:n] = data
        except TypeError:
            import array
            if not isinstance(b, array.array):
                raise
            b[:n] = array.array('b', data)

        return n