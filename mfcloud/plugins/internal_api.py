import logging
import os
import inject
from mfcloud.application import ApplicationController
from mfcloud.events import EventBus
from mfcloud.plugins import Plugin
from twisted.internet.defer import inlineCallbacks
import txredisapi
from twisted.python import log

logger = logging.getLogger('mfcloud.plugin.dns')


from twisted.internet import protocol, reactor, endpoints

class Echo(protocol.Protocol):
    def dataReceived(self, data):
        log.msg('Message in: %s' % data)
        self.transport.write('ok|You wrote: %s\n' % data)

class EchoFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return Echo()

class InternalApiPlugin(Plugin):
    eb = inject.attr(EventBus)
    app_controller = inject.attr(ApplicationController)
    redis = inject.attr(txredisapi.Connection)

    def listen(self):
        endpoints.serverFromString(reactor, "unix:/var/run/mfcloud").listen(EchoFactory())

    def __init__(self):
        super(InternalApiPlugin, self).__init__()

        self.listen()

        api_file = os.path.dirname(os.path.dirname(__file__)) + '/api.py'
        os.chown(api_file, 0, 0)
        os.chmod(api_file, 0744)

        log.msg('Api plugin started')
