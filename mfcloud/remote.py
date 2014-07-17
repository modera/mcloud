import sys
from twisted.internet import reactor, defer
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.protocol import Protocol
from twisted.python import log

from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketClientProtocol, WebSocketClientFactory


class WebsocketServerProtocol(WebSocketServerProtocol):
    def __init__(self):
        pass

    def onConnect(self, request):
        pass

    def onOpen(self):
        self.factory.server.clients.append(self)

    def onMessage(self, payload, isBinary):
        self.factory.server.on_message(payload, isBinary)

    def onClose(self, wasClean, code, reason):
        pass


class Server(object):
    def __init__(self, port=7080):
        self.tasks = {}
        self.port = port
        self.clients = []

    def on_message(self, payload, isBinary):
        pass

    def shutdown(self):
        for protocol in self.clients:
            protocol.sendClose()

    def register_task(self, name, callback):
        self.tasks['name'] = callback

    def bind(self):
        factory = WebSocketServerFactory("ws://localhost:%s" % self.port, debug=False)
        factory.server = self
        factory.protocol = WebsocketServerProtocol

        reactor.listenTCP(self.port, factory)


class WebsocketClientProtocol(WebSocketClientProtocol):
    def __init__(self):
        pass

    client = None

    def onConnect(self, response):
        pass

    def onOpen(self):
        self.client.protocol = self
        self.client.onc.callback(True)

        #self.sendMessage(u"Hello, world!".encode('utf8'))
        #self.sendMessage(b"\x00\x01\x03\x04", isBinary=True)

    def onMessage(self, payload, isBinary):
        #if isBinary:
        #    print("Binary message received: {0} bytes".format(len(payload)))
        #else:
        #    print("Text message received: {0}".format(payload.decode('utf8')))

        self.client.on_message(payload)

    def onClose(self, wasClean, code, reason):
        pass


class Client(object):
    def __init__(self, port=7080):
        self.port = port
        self.onc = None
        self.protocol = None

    def send(self, data):
        return self.protocol.sendMessage(data)

    def shutdown(self):
        self.protocol.sendClose()

    def on_message(self, data):
        pass

    def connect(self):
        factory = WebSocketClientFactory("ws://localhost:%s" % self.port, debug=False)
        factory.protocol = WebsocketClientProtocol
        factory.protocol.client = self

        point = TCP4ClientEndpoint(reactor, "localhost", self.port)
        point.connect(factory)

        self.onc = defer.Deferred()
        return self.onc


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