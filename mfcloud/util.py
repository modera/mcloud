from contextlib import contextmanager
from abc import ABCMeta
from flask import logging
import inject
from twisted.internet import reactor
from twisted.python import log

class Interface(object):
    __metaclass__ = ABCMeta

@contextmanager
def inject_services(configurator):
    inject.clear_and_configure(configurator)
    yield
    inject.clear()

@contextmanager
def injector(bind_config):

    def configurator(binder):
        for key, val in bind_config.items():
            binder.bind(key, val)

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
