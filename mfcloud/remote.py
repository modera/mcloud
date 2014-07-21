import json
import sys
import inject
from mfcloud.events import EventBus
from mfcloud.websocket import MdcloudWebsocketClientProtocol, MdcloudWebsocketServerProtocol
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks
from twisted.internet.endpoints import TCP4ClientEndpoint

from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketClientFactory
import txredisapi


class Server(object):
    redis = inject.attr(txredisapi.Connection)
    eb = inject.attr(EventBus)

    def __init__(self, port=7080):
        self.tasks = {}
        self.port = port
        self.clients = []

        self.request_map = {}

    @inlineCallbacks
    def on_message(self, payload, is_binary=False):
        """
        Method is called when new message arrives from client
        """
        yield self.redis.incr('mfcloud-ticket-id')

    def on_client_connect(self, client):
        """
        Method is called when new client is here
        """
        self.clients.append(client)

    def on_client_disconnect(self, client, wasClean, code, reason):
        """
        Method is called when client disconnects
        """
        self.clients.remove(client)

    def shutdown(self):
        """
        Terminate all client sessions
        """
        for protocol in self.clients:
            protocol.sendClose()

        self.clients = []

    def register_task(self, name, callback):
        """
        Add new task to task list
        """
        self.tasks[name] = callback

    def bind(self):
        """
        Start listening on the port specified
        """
        factory = WebSocketServerFactory("ws://localhost:%s" % self.port, debug=False)
        factory.server = self
        factory.protocol = MdcloudWebsocketServerProtocol

        reactor.listenTCP(self.port, factory)


class Client(object):
    def __init__(self, port=7080):
        self.port = port
        self.onc = None
        self.protocol = None
        self.request_id = 0

    def send(self, data):
        return self.protocol.sendMessage(data)

    def shutdown(self):
        self.protocol.sendClose()

    def on_message(self, data, is_binary=False):
        pass

    def connect(self):
        factory = WebSocketClientFactory("ws://localhost:%s" % self.port, debug=False)
        factory.protocol = MdcloudWebsocketClientProtocol
        factory.protocol.client = self

        point = TCP4ClientEndpoint(reactor, "localhost", self.port)
        point.connect(factory)

        self.onc = defer.Deferred()
        return self.onc

    def call(self, task, *args):
        self.request_id += 1

        msg = {
            'id': self.request_id,
            'task': task,
            'args': args,
        }
        data = 'task:%s' % json.dumps(msg)

        return self.send(data)


class Task(object):
    def __init__(self, name):
        super(Task, self).__init__()

        self.name = name


if __name__ == '__main__':
    from twisted.python import log

    log.startLogging(sys.stdout)

    server = Server(port=9999)
    server.bind()

    reactor.run()