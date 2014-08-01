import json
import logging
import inject
from mfcloud.application import ApplicationController
from mfcloud.events import EventBus
from mfcloud.plugins import Plugin
from mfcloud.txdocker import IDockerClient, NotFound
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks
from twisted.python import log

logger = logging.getLogger('mfcloud.monitor')


class DockerMonitorPlugin(Plugin):
    client = inject.attr(IDockerClient)
    event_bus = inject.attr(EventBus)
    app_controller = inject.attr(ApplicationController)

    def __init__(self):
        super(DockerMonitorPlugin, self).__init__()
        logger.info('Docker monitoring plugin started')

        reactor.callLater(0, self.start)

    def on_event(self, event):
        log.msg('New docker event: %s' % event)
        self.event_bus.fire_event('containers.updated')

    def attach_to_events(self, *args):
        logger.info('Start monitoring docker events')
        return self.client.events(self.on_event)

    @inlineCallbacks
    def start(self):
        logger.info('Checking docker ..')

        info = yield self.client.version()

        v = tuple(map(int, (info['Version'].split("."))))

        if v < (0, 11, 1):
            reactor.stop()
            print('Please update docker, to version above 0.11.1. Current version: %s' % info['Version'])

        else:
            yield self.attach_to_events()


 #def __init__(self):
    #    self.listening = []
    #
    #def _listen(self, container_id):
    #    def on_log(log):
    #        log = log.encode("base64")
    #        return self.event_bus.fire_event('container-log', container_id=container_id, log=log)
    #
    #    def done(result):
    #        logger.debug('Done following logs from container %s.' % container_id)
    #        self.listening.remove(container_id)
    #
    #    def on_err(failure):
    #        failure.trap(NotFound)  # just skip on 404
    #        logger.debug('Skip. No logs for container %s. Reason: %s' % (container_id, failure.value.message))
    #        self.listening.remove(container_id)
    #        return None
    #
    #    d = self.client.logs(container_id, on_log)
    #    d.addCallback(done)
    #    d.addErrback(on_err)
    #    return d
    #
    #def listen_logs(self, container):
    #    pass
    #    # if container['Id'] not in self.listening:
    #    #     self.listening.append(container['Id'])
    #    #     logger.debug('Start following logs from container %s.' % container['Id'])
    #    #     reactor.callLater(0, self._listen, container['Id'])