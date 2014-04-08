from contextlib import contextmanager
from abc import ABCMeta
import inject


class Interface(object):
    __metaclass__ = ABCMeta

@contextmanager
def inject_services(configurator):
    inject.clear_and_configure(configurator)
    yield
    inject.clear()
