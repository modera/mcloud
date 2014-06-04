import json
import logging
import inject
from mfcloud.application import ApplicationController
from mfcloud.events import EventBus
from mfcloud.txdocker import IDockerClient, NotFound
from twisted.internet import reactor, defer

logger = logging.getLogger('mfcloud.monitor')


class DockerMonitor(object):
    client = inject.attr(IDockerClient)
    event_bus = inject.attr(EventBus)
    app_controller = inject.attr(ApplicationController)

    def __init__(self):
        self.listening = []

    def _listen(self, container_id):
        def on_log(log):
            log = log.encode("base64")
            return self.event_bus.fire_event('container-log', container_id=container_id, log=log)

        def done(result):
            logger.debug('Done following logs from container %s.' % container_id)
            self.listening.remove(container_id)

        def on_err(failure):
            failure.trap(NotFound)  # just skip on 404
            logger.debug('Skip. No logs for container %s. Reason: %s' % (container_id, failure.value.message))
            self.listening.remove(container_id)
            return None

        d = self.client.logs(container_id, on_log)
        d.addCallback(done)
        d.addErrback(on_err)
        return d

    def listen_logs(self, container):
        if container['Id'] not in self.listening:
            self.listening.append(container['Id'])
            logger.debug('Start following logs from container %s.' % container['Id'])
            reactor.callLater(0, self._listen, container['Id'])

    def update_container_list(self, *args):
        def _update(containers):

            for container in containers:
                self.listen_logs(container)

            container_info = [self.client.inspect(container['Id']) for container in containers]

            def send_out_event(containers):

                def on_apps_listed(app_data):
                    self.event_bus.fire_event('containers-updated', list=containers, apps=app_data)

                ad = self.app_controller.list()
                ad.addCallback(on_apps_listed)

                return ad

            d = defer.gatherResults(container_info, consumeErrors=True)
            d.addCallback(send_out_event)
            return d


        d = self.client.list()
        d.addCallback(_update)

    def on_event(self, event):
        logging.debug('New docker event: %s' % event)
        # event = json.loads(event)
        reactor.callLater(0, self.update_container_list)

    def attach_to_events(self, *args):
        logging.info('Start monitoring docker events')
        return self.client.events(self.on_event)

    def start(self):
        logging.info('Checking docker')

        def check_version(info):

            v = tuple(map(int, (info['Version'].split("."))))

            print v

            if v < (0, 11, 1):
                reactor.stop()
                print('Please update docker, to version above 0.11.1. Current version: %s' % info['Version'])



        d = self.client.version()
        d.addCallback(check_version)
        d.addCallback(self.update_container_list)
        d.addCallback(self.attach_to_events)

        return d
