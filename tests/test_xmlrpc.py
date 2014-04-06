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

        def xmlrpc_echo(self, x):
            """
            Return all passed args.
            """
            return x

        def xmlrpc_add(self, a, b):
            """
            Return sum of arguments.
            """
            return a + b

        def xmlrpc_fault(self):
            """
            Raise a Fault indicating that the procedure should not be used.
            """
            raise xmlrpc.Fault(123, "The fault procedure is faulty.")


    r = Example()
    reactor.listenTCP(7080, server.Site(r))



    def printValue(value):
        print repr(value)
        reactor.stop()

    def printError(error):
        print 'error', error
        reactor.stop()

    proxy = Proxy('http://127.0.0.1:7080')
    result = yield proxy.callRemote('add', 3, 5)

    assert result == 8
