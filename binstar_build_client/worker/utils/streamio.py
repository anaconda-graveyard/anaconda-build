"""
Threaded class to stream io from an iterator to a writeable file object
"""
import logging
from threading import Thread, Event
import time


log = logging.getLogger(__name__)


def stream_line_iterator(stream):
    """
    The builin file object does not work as an iterator in this case
    This is used as a wrapper 
    """
    data = stream.readline()
    while data:
        yield data
        data = stream.readline()


class IOStream(Thread):
    """
    Thread subclass 
    :param line_iterator: An iterable that yields output 
    :param outstream: The output to write to (must only have .write method)
    :param iotimeout: The duration in seconds to wait before calling `timeout_callback` if no output is yielded
    :param timeout: The duration in seconds to wait before calling `timeout_callback`
    :param timeout_callback: a function with the definition timeout_callback([True|False])
         called with true if `iotimeout` is reached otherwise `timeout` was reached
    """
    def __init__(self, line_iterator, outstream, iotimeout=None, timeout=None, timeout_callback=None):

        if isinstance(line_iterator, file):
            line_iterator = stream_line_iterator(line_iterator)

        self.line_iterator = line_iterator
        self.outstream = outstream
        self._start_time = self._last_io = time.time()
        self.iotimeout = iotimeout
        self.timeout = timeout
        self.timeout_callback = timeout_callback
        self.finished_event = Event()

        self._timeout_loop_thread = None
        Thread.__init__(self, None, name='iostream')

    def run(self):
        'Loop over lines in self.line_iterator and write them to outstream'
        try:

            for line in self.line_iterator:
                self._last_io = time.time()
                self.outstream.write(line)
                # self.outstream.flush()

                if getattr(self.outstream, 'terminate_build', False):
                    self.timeout_callback(reason='user_request')

        finally:
            self.finished_event.set()

    def start(self):

        if self.iotimeout or self.timeout:
            self._timeout_loop_thread = Thread(target=self.timeout_loop, name='timeout_loop')
            self._timeout_loop_thread.start()

        Thread.start(self)

    def timeout_loop(self):
        'Loop until finished_event is set'
        while not self.finished_event.wait(1):

            elapsed_io = time.time() - self._last_io

            if self.iotimeout and elapsed_io >= self.iotimeout:
                self.timeout_callback(reason='iotimeout')
                return

            elapsed_total = time.time() - self._start_time
            if self.timeout and elapsed_total >= self.timeout:
                self.timeout_callback(reason='timeout')
                return
