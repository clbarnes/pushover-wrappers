import pushover as po
import time
from datetime import timedelta
from io import StringIO
import sys


def sec_to_hms(secs):
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)
    return '{:.02d}:{:02d}:{:02.0f}'.format(h, m, s)


def push_exceptions(fn):
    """
    A decorator which catches any exceptions thrown by the wrapped function and reports them by Pushover.
    """
    def ret_fn(*args, **kwargs):
        try:
            start_time = time.time()
            return fn(*args, **kwargs)
        except Exception as e:
            fail_time = time.time()
            exec_time = timedelta(seconds=fail_time - start_time)
            title = "Error in {}:{} after {}".format(fn.__module__, fn.__name__, exec_time)
            message = str(e)

            po.Client().send_message(message, title=title)
            raise e

    return ret_fn


def push_success(fn):
    """
    A decorator which reports (including execution time) by Pushover whenever the wrapped function completes without error.
    """
    def ret_fn(*args, **kwargs):
        start_time = time.time()
        result = ret_fn(*args, **kwargs)
        exec_time = timedelta(seconds=time.time() - start_time)
        message = "Completed {}:{} after {}".format(fn.__module__, fn.__name__, exec_time)
        po.Client().send_message(message, title='Success!')
        return result

    return ret_fn


class PushContext():
    """
    A context manager which reports by pushover when the code in the block completes, returning the stdout if successful and stderr otherwise.
    """
    def __init__(self):
        self.start_time = None
        self.block_label = ''
        self.old_stdout = None
        self.old_stderr = None
        self.my_stdout = None
        self.my_stderr = None

    def __enter__(self, block_label):
        self.start_time = time.time()
        self.block_label = block_label
        self.old_stdout = sys.stdout
        sys.stdout = self.my_stdout = StringIO()
        self.old_stderr = sys.stderr
        sys.stderr = self.my_stderr = StringIO()

    def __exit__(self):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        exectime = time.time() - self.start_time
        status, message = self.get_status_message()
        if status == 'failed':
            sys.stderr.write(message)
        else:
            sys.stdout.write(message)
        po.Client().send_message(message, title='{} {} after {}'.format(self.block_label, status, sec_to_hms(exectime)))

    def get_status_message(self):
        if self.my_stderr.getvalue():
            return 'failed',  self.my_stderr.getvalue()
        else:
            return 'succeeded', self.my_stdout.getvalue()

