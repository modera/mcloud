from contextlib import contextmanager
from abc import ABCMeta
import inject
import os
from twisted.internet import reactor


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


import sys

@contextmanager
def safe_chdir(dir):
    before = os.getcwd()
    os.chdir(dir)
    yield
    os.chdir(before)

def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")