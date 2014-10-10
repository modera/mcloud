import json
import logging
import os

import inject
import txredisapi
from twisted.python import log

from mcloud.application import ApplicationController
from mcloud.events import EventBus
from mcloud.plugins import Plugin


logger = logging.getLogger('mcloud.plugin.dns')


from twisted.internet import protocol, reactor, endpoints


class InternalApiProtocol(protocol.Protocol):

    eb = inject.attr(EventBus)
    """ @type: EventBus """

    def dataReceived(self, data):
        log.msg('Message in: %s' % data)

        msg = json.loads(data)
        self.eb.fire_event('api.%s.%s' % (msg['hostname'], msg['command']), my_args=msg['args'])
        self.transport.write(json.dumps({'status': 'ok'}))


class InternalApiProtocolFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return InternalApiProtocol()


class InternalApiPlugin(Plugin):

    app_controller = inject.attr(ApplicationController)
    redis = inject.attr(txredisapi.Connection)

    def listen(self):
        endpoints.serverFromString(reactor, "unix:/var/run/mcloud").listen(InternalApiProtocolFactory())

    def __init__(self):
        super(InternalApiPlugin, self).__init__()

        self.listen()

        api_file = os.path.dirname(os.path.dirname(__file__)) + '/api.py'
        os.chmod(api_file, 0744)

        log.msg('Api plugin started')
