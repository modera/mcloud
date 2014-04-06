import pytest
from twisted.web import xmlrpc, server
from twisted.internet import reactor
from twisted.web.xmlrpc import Proxy

@pytest.inlineCallbacks
def test_rpc():

    class Example(xmlrpc.XMLRPC):
        """
        An example object to be published.
        """

        def xmlrpc_add(self, a, b):
            """
            Return sum of arguments.
            """
            return a + b

    r = Example()
    reactor.listenTCP(7080, server.Site(r))

    proxy = Proxy('http://127.0.0.1:7080')
    result = yield proxy.callRemote('add', 3, 5)

    assert result == 8
