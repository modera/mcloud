import json
import logging
import sys
from mfcloud.rpc_client import ApiRpcClient
from twisted.internet import reactor
from twisted.internet.error import ConnectionRefusedError
from twisted.internet.protocol import Protocol, Factory
from twisted.web.xmlrpc import Proxy
from txzmq import ZmqFactory, ZmqEndpoint, ZmqSubConnection
from txsockjs.factory import SockJSFactory


logger = logging.getLogger('mfcloud.webclient_server')


class WebsocketProtocol(Protocol):

    def __init__(self):
        self.factory = None

        self.rid_map = {}

    def send_error(self, message, data=None):
        self.transport.write(json.dumps({
            'type': 'error',
            'message': message,
            'data': data
        }))

    def dataReceived(self, data):

        logger.debug('[Websocket] %s' % data)

        message = json.loads(data)

        if not 'requestId' in message:
            return self.send_error('Request id not specified, on last request!')

        if not 'request' in message:
            return self.send_error('Request is not specified, on request with id %s!' % message['requestId'])

        if not 'args' in message:
            args = []
        else:
            args = message['args']

        d = self.factory.proxy.callRemote('task_start', message['request'], *args)

        def ready(result):
            logger.debug('rpc response:%s' % result)
            ticket_id = int(result['ticket_id'])
            self.rid_map[ticket_id] = message['requestId']
            self.factory.tid_map[ticket_id] = self

        def failed(failure):
            if failure.type == ConnectionRefusedError:
                self.send_error('Connection to Modera Cloud server failure. Server is not started?')
            else:
                self.send_error('Failed to execute the task: %s' % failure.getErrorMessage())

        d.addCallback(ready)
        d.addErrback(failed)

    def handle_message(self, ticket_id, type, message):
        request_id = self.rid_map[ticket_id]

        self.transport.write(json.dumps({
            'requestId': request_id,
            'type': type,
            'message': message
        }))

        if type != 'log':
            del self.factory.tid_map[ticket_id]
            del self.rid_map[ticket_id]

    def connectionLost(self, *args, **kwargs):
        Protocol.connectionLost(self, *args, **kwargs)

        for ticket_id, protocol in self.factory.tid_map.items():
            if protocol == self:
                del self.factory.tid_map[ticket_id]



class ZmqAwareWebSockJsFactory(Factory):

    def __init__(self):
        self.subscribers = []

        self.zf2 = ZmqFactory()
        self.e2 = ZmqEndpoint('connect', 'tcp://127.0.0.1:5555')
        self.s2 = ZmqSubConnection(self.zf2, self.e2)
        self.s2.subscribe("")
        self.s2.gotMessage = self._on_message

        self.proxy = Proxy('http://127.0.0.1:7080')

        self.tid_map = {}
        self.reactor = reactor

    def _on_message(self, message, tag, attempt=0):

        ticket_id = int(tag.split('-')[-1])
        message_type = '-'.join(tag.split('-')[:-1])

        if not ticket_id in self.tid_map:
            logger.debug('delaying zmq message. Ticket id %s, map: %s', ticket_id, self.tid_map.keys())
            if attempt < 5:
                self.reactor.callLater(0.1, self._on_message, message, tag, attempt + 1)
            return

        logger.debug('zmq message: %s tag: %s', message, tag)

        protocol = self.tid_map[ticket_id]

        if message_type == 'task-completed':
            protocol.handle_message(ticket_id, 'result', message)

        elif message_type == 'task-failed':
            protocol.handle_message(ticket_id, 'failure', message)

        elif message_type == 'log':
            protocol.handle_message(ticket_id, 'log', message)


if __name__ == '__main__':

    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(logging.Formatter())
    console_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG)
    root_logger.debug('Logger initialized')

    reactor.listenTCP(9911, SockJSFactory(ZmqAwareWebSockJsFactory.forProtocol(WebsocketProtocol)))

    reactor.run()
