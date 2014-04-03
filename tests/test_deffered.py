import pytest
from twisted.internet import defer, reactor


def boo():
    d = defer.Deferred()
    reactor.callLater(0.1, d.callback, 10)
    return d

@pytest.inlineCallbacks
def test_boo_defferred():
    a = yield boo()
    assert 10 == a