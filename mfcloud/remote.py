import json
import sys
import inject
from mfcloud.events import EventBus
from mfcloud.rpc_server import ApiRpcServer
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks
from twisted.internet.endpoints import TCP4ClientEndpoint

from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketClientFactory
import txredisapi

from twisted.python import log

from autobahn.twisted.websocket import WebSocketClientProtocol, WebSocketServerProtocol


class ApiError(Exception):
    pass


class MdcloudWebsocketServerProtocol(WebSocketServerProtocol):
    def __init__(self):
        pass

    def onConnect(self, request):
        pass

    def onOpen(self):
        self.factory.server.on_client_connect(self)

    def onClose(self, wasClean, code, reason):
        self.factory.server.on_client_disconnect(self, wasClean, code, reason)

    def onMessage(self, payload, isBinary):

        log.msg('Websocket server in: %s' % payload)
        #print(self.factory.server.on_message())

        reactor.callLater(0, self.factory.server.on_message, self, payload, isBinary)



class Server(object):
    redis = inject.attr(txredisapi.Connection)
    eb = inject.attr(EventBus)
    rpc_server = inject.attr(ApiRpcServer)

    def __init__(self, port=7080):
        self.task_map = {}
        self.port = port
        self.clients = []

    def sendEvent(self, client, event_name, data):
        return client.sendMessage(json.dumps({
            'type': 'response',
            'id': request_id,
            'success': success,
            'response': response
        }))


    def sendResponse(self, client, request_id, response, success=True):
        return client.sendMessage(json.dumps({
            'type': 'response',
            'id': request_id,
            'success': success,
            'response': response
        }))

    @inlineCallbacks
    def on_message(self, client, payload, is_binary=False):
        #"""
        #Method is called when new message arrives from client
        #"""
        #ticket_id = yield self.redis.incr('mfcloud-ticket-id')

        log.msg('Incomming message: %s' % payload)

        try:
            data = json.loads(payload)

            if data['task'] == 'ping':
                yield self.sendResponse(client, data['id'], 'pong')

            elif data['task'] == 'task_start':
                ticket_id = yield self.rpc_server.task_start(client, *data['args'], **data['kwargs'])
                yield self.sendResponse(client, data['id'], ticket_id)
            else:
                yield self.sendResponse(client, data['id'], 'Unknown command', success=False)

        except Exception:
            log.err()



    def on_client_connect(self, client):
        """
        Method is called when new client is here
        """
        self.clients.append(client)
        log.msg('Client connected')

    def on_client_disconnect(self, client, wasClean, code, reason):
        """
        Method is called when client disconnects
        """
        if client in self.clients:
            self.clients.remove(client)

        log.msg('Client disconnected')

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



class MdcloudWebsocketClientProtocol(WebSocketClientProtocol):
    def __init__(self):
        pass

    client = None

    def onConnect(self, response):
        pass

    def onOpen(self):
        self.client.protocol = self
        self.client.onc.callback(True)

    def onMessage(self, payload, is_binary):
        """
        is_binary affects method of message encoding:

        if is_binary:
            print("Binary message received: {0} bytes".format(len(payload)))
        else:
            print("Text message received: {0}".format(payload.decode('utf8')))
        """

        log.msg('Websocket client in: %s' % payload)
        reactor.callLater(0, self.client.on_message, payload, is_binary)



    def onClose(self, wasClean, code, reason):
        pass


class Client(object):
    def __init__(self, port=7080):
        self.port = port
        self.onc = None
        self.protocol = None
        self.request_id = 0
        self.request_map = {}

        self.task_map = {}

    def send(self, data):
        log.msg('Send message: %s' % data)
        return self.protocol.sendMessage(data)

    def shutdown(self):
        self.protocol.sendClose()

    def on_message(self, data, is_binary=False):

        log.msg('Client in: %s' % data)

        data = json.loads(data)

        try:
            if data['id'] in self.request_map:
                if data['success']:
                    return self.request_map[data['id']].callback(data['response'])
                else:
                    return self.request_map[data['id']].errback(ApiError(data['response']))
            else:
                raise Exception('Unknown request id: %s' % data['id'])
        except ValueError:
            raise Exception('Invalid json: %s' % data)

    def connect(self):
        factory = WebSocketClientFactory("ws://localhost:%s" % self.port, debug=False)
        factory.protocol = MdcloudWebsocketClientProtocol
        factory.protocol.client = self

        point = TCP4ClientEndpoint(reactor, "localhost", self.port)
        point.connect(factory)

        self.onc = defer.Deferred()
        return self.onc

    def call_sync(self, task, *args, **kwargs):
        d = defer.Deferred()

        self.request_id += 1
        _id = self.request_id

        self.request_map[_id] = d

        msg = {
            'id': _id,
            'task': task,
            'args': args,
            'kwargs': kwargs,
        }

        self.send(json.dumps(msg))



        return d


    @inlineCallbacks
    def call(self, task, *args, **kwargs):

        task.id = yield self.call_sync('task_start', task.name, *args, **kwargs)
        task.is_running = True

        self.task_map[task.id] = task

        defer.returnValue(task)


class Task(object):

    def __init__(self, name):
        super(Task, self).__init__()

        self.name = name
        self.id = None
        self.is_running = False

        self.data = []
        self.response = None
        self.failure = False

    def on_progress(self, data):
        self.data.append(data)

    def on_success(self, result):
        self.response = result
        self.is_running = False

    def on_failure(self, result):
        self.is_running = False
        self.response = result
        self.failure = True

if __name__ == '__main__':
    from twisted.python import log

    log.startLogging(sys.stdout)

    server = Server(port=9999)
    server.bind()

    reactor.run()