import pytest
from autobahn.twisted.util import sleep
from mcloud.util import TxTimeoutEception, txtimeout
from twisted.internet import defer, reactor
import time

def boo():
    d = defer.Deferred()
    reactor.callLater(0.1, d.callback, 10)
    return d

@pytest.inlineCallbacks
def test_boo_defferred():
    a = yield boo()
    assert 10 == a


@pytest.inlineCallbacks
def test_sleep():
    start = time.time()
    a = yield sleep(0.05)
    end = time.time()
    assert 0.1 > (end - start) > 0.05

@pytest.inlineCallbacks
def test_timeout():

    yield txtimeout(sleep(0.2), 0.3, 'foo')

    with pytest.raises(TxTimeoutEception):
        yield txtimeout(sleep(3), 0.3, 'boo')