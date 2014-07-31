import logging
import inject
from mfcloud.application import ApplicationController
from mfcloud.events import EventBus
from mfcloud.plugins import Plugin
from twisted.internet.defer import inlineCallbacks
import txredisapi
from twisted.python import log

logger = logging.getLogger('mfcloud.plugin.dns')


class DnsPlugin(Plugin):
    eb = inject.attr(EventBus)
    app_controller = inject.attr(ApplicationController)
    redis = inject.attr(txredisapi.Connection)

    @inlineCallbacks
    def dump(self, apps_list):
        apps = {}

        for app in apps_list:
            for service in app['services']:
                apps[service['fullname']] = service['ip']

            if 'web_service' in app and app['web_service']:
                apps[app['fullname']] = app['web_ip']

            if 'public_urls' in  app and app['public_urls'] and 'web_ip' in app:
                for url in app['public_urls']:
                    apps[url] = app['web_ip']

        logger.info('Installing new app list: %s' % str(apps))

        yield self.redis.delete('domain')

        if len(apps) > 1:
            yield self.redis.hmset('domain', apps)
        elif len(apps) == 1:
            yield self.redis.hset('domain', apps.keys()[0], apps.values()[0])

    def __init__(self):
        super(DnsPlugin, self).__init__()
        self.eb.on('containers.updated', self.containers_updated)

        logger.info('Dns plugin started')

    @inlineCallbacks
    def containers_updated(self, *args, **kwargs):
        logger.info('Containers updated: dumping haproxy config.')

        data = yield self.app_controller.list()
        self.dump(data)