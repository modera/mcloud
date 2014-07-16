import sys
from twisted.internet import reactor, defer
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.protocol import Protocol, Factory, BaseProtocol
from twisted.web.server import Site
from txsockjs.factory import SockJSFactory
from twisted.python import log
from txsockjs.websockets import _WebSocketsFactory


class ServerProtocol(Protocol):
    def connectionMade(self):
        self.transport.write('oo!')

    def dataReceived(self, data):
        log.msg('Server received data: %s' % data)
        self.server.on_message(data)


class ServerFactory(SockJSFactory):
    def __init__(self, server, options=None):
        factory = Factory.forProtocol(ServerProtocol)
        SockJSFactory.__init__(self, factory, options)

        self.server = server

    def buildProtocol(self, addr):
        protocol = SockJSFactory.buildProtocol(self, addr)
        protocol.server = self.server
        self.server.clients.append(protocol)
        return protocol


class Server(object):
    def __init__(self, port=7080):
        self.tasks = {}
        self.port = port
        self.clients = []

    def on_message(self, message):
        pass

    def register_task(self, name, callback):
        self.tasks['name'] = callback

    def bind(self):
        reactor.listenTCP(self.port, ServerFactory(self))


class ClientProtocol(Protocol):
    def connectionMade(self):
        log.msg('Client connected!')
        self.transport.write('bazbaz')

    def dataReceived(self, data):
        log.msg('Client received data: ' % data)


from autobahn.twisted.websocket import WebSocketClientProtocol, WebSocketClientFactory


class MyClientProtocol(WebSocketClientProtocol):
    client = None

    def onConnect(self, response):
        print("Server connected: {0}".format(response.peer))

    def onOpen(self):
        print("WebSocket connection open.")

        self.sendMessage(u"Hello, world!".encode('utf8'))
        self.sendMessage(b"\x00\x01\x03\x04", isBinary=True)

    def onMessage(self, payload, isBinary):
        if isBinary:
            print("Binary message received: {0} bytes".format(len(payload)))
        else:
            print("Text message received: {0}".format(payload.decode('utf8')))

        self.client.on_message(payload)

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))


class Client(object):
    def __init__(self, port=7080):
        self.port = port

    def send(self, data):
        self.protocol.sendMessage(data)

    def on_message(self, data):
        pass

    def on_conneced(self, protocol):
        self.protocol = protocol

    def connect(self):
        factory = WebSocketClientFactory("ws://localhost:%s/websocket" % self.port, debug=False)
        factory.protocol = MyClientProtocol
        factory.protocol.client = self

        point = TCP4ClientEndpoint(reactor, "localhost", self.port)
        d = point.connect(factory)
        d.addCallback(self.on_conneced)
        return d


class Task(object):
    def __init__(self, name, *args):
        super(Task, self).__init__()

    def connect(self):
        pass


if __name__ == '__main__':
    from twisted.python import log

    log.startLogging(sys.stdout)

    server = Server(port=9999)
    server.bind()

    reactor.run()