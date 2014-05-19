import json
import logging
import inject
from mfcloud.events import EventBus
from mfcloud.txdocker import IDockerClient

logger = logging.getLogger('mfcloud.monitor')

class DockerMonitor(object):

    client = inject.attr(IDockerClient)
    event_bus = inject.attr(EventBus)

    # def update_container_list(self):
    #     def _update(containers):
    #         print containers
    #
    #     d = self.client.list()
    #     d.addCallback(_update)
    #
    #     return d

    def on_event(self, event):
        logging.debug('New docker event: %s' % event)
        # event = json.loads(event)
        # return self.update_container_list()


    def start(self):
        logging.info('Start monitoring docker events')
        self.client.events(self.on_event)
