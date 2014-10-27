from Queue import Queue, Empty
from contextlib import contextmanager
from abc import ABCMeta
import inject
import os
from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure


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

class TxTimeoutEception(Exception):
    pass

def txtimeout(deferred, timeout, fail):

    def _raise():
        deferred.errback(Failure(TxTimeoutEception(fail)))

    delayedCall = reactor.callLater(timeout, _raise)

    def gotResult(result):
        if delayedCall.active():
            delayedCall.cancel()
        return result
    deferred.addBoth(gotResult)

    return deferred

class ValidationError(Exception):
    pass

class UserError(Exception):
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


from twisted.internet import protocol
from twisted.internet import reactor


class LessLongTextProtocol(protocol.ProcessProtocol):
    def __init__(self, long_text, on_exit):
        self.long_text = long_text
        self.on_exit = on_exit

    def connectionMade(self):
        print "Connected"
        # self.transport.write(self.long_text.encode('utf-8'))
        self.transport.write('kuku')
        self.transport.closeStdin()



    def errReceived(self, data):
        protocol.ProcessProtocol.errReceived(self, data)
        print(data)

    def outReceived(self, data):
        protocol.ProcessProtocol.outReceived(self, data)

        print data


    def processEnded(self, reason):
        self.on_exit.callback(True)
