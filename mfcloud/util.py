from contextlib import contextmanager
from abc import ABCMeta
import inject
from twisted.internet import reactor


class Interface(object):
    __metaclass__ = ABCMeta

@contextmanager
def inject_services(configurator):
    inject.clear_and_configure(configurator)
    yield
    inject.clear()


def txtimeout(deferred, timeout, fail):
    delayedCall = reactor.callLater(timeout, fail)

    def gotResult(result):
        if delayedCall.active():
            delayedCall.cancel()
        return result
    deferred.addBoth(gotResult)

    return deferred

class ValidationError(Exception):
    pass
