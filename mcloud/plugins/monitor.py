import inject
from mcloud.application import ApplicationController
from mcloud.events import EventBus
from mcloud.plugin import IMcloudPlugin
from mcloud.plugins import Plugin
from mcloud.txdocker import IDockerClient
from twisted.internet import reactor
from twisted.python import log
from zope.interface import implements


class DockerMonitorPlugin(Plugin):
    """
    Monitors docker events and emmits "containers.updated" event when non-internal
     containers change their state.
    """
    implements(IMcloudPlugin)

    client = inject.attr(IDockerClient)
    event_bus = inject.attr(EventBus)
    app_controller = inject.attr(ApplicationController)

    def setup(self):
        reactor.callLater(0, self.attach_to_events)

    def on_event(self, event):
        if not self.app_controller.is_internal(event['id']):
            log.msg('New docker event: %s' % event)
            self.event_bus.fire_event('containers.updated', event)

    def attach_to_events(self, *args):
        log.msg('Start monitoring docker events')
        return self.client.events(self.on_event)
