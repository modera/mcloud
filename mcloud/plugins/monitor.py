import json
import logging
import inject
from mcloud.application import ApplicationController
from mcloud.events import EventBus
from mcloud.plugins import Plugin
from mcloud.txdocker import IDockerClient
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.python import log


class DockerMonitorPlugin(Plugin):
    client = inject.attr(IDockerClient)
    event_bus = inject.attr(EventBus)
    app_controller = inject.attr(ApplicationController)

    # @inlineCallbacks
    def setup(self):



        reactor.callLater(0, self.attach_to_events)

    def on_event(self, event):
        if not self.app_controller.is_internal(event['id']):
            log.msg('New docker event: %s' % event)
            self.event_bus.fire_event('containers.updated', event)

    def attach_to_events(self, *args):
        log.msg('Start monitoring docker events')
        return self.client.events(self.on_event)



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