import logging
import inject
from mcloud.application import ApplicationController

from mcloud.events import EventBus
from mcloud.plugins import Plugin
from mcloud.service import Service

from mcloud.container import InlineDockerfileImageBuilder

from twisted.internet.defer import inlineCallbacks
import txredisapi
from twisted.python import log

logger = logging.getLogger('mcloud.plugin.dns')


class DnsPlugin(Plugin):
    eb = inject.attr(EventBus)
    app_controller = inject.attr(ApplicationController)
    redis = inject.attr(txredisapi.Connection)
    web_listen_ip = inject.attr('dns-server')
    settings = inject.attr('settings')
    """ @var McloudConfiguration """

    @inlineCallbacks
    def dump(self, apps_list):
        apps = {
        #     'mcloud.lh': self.settings.web_ip
        }

        for app in apps_list:
            for service in app['services']:
                apps[service['fullname']] = service['ip']

            if 'web_service' in app and app['web_service']:
                apps[app['fullname']] = app['web_ip']

            if 'public_urls' in app and app['public_urls'] and 'web_ip' in app:
                for target in app['public_urls']:
                    if not target['service']:
                        apps[target['url']] = app['web_ip']
                    else:
                        for service in app['services']:
                            if service['shortname'] == target['service']:
                                apps[target['url']] = service['ip']

        log.msg('Installing new dns list: %s' % str(apps))

        yield self.redis.delete('domain')

        if len(apps) > 1:
            yield self.redis.hmset('domain', apps)
        elif len(apps) == 1:
            yield self.redis.hset('domain', apps.keys()[0], apps.values()[0])


    @inlineCallbacks
    def setup(self):

        self.dnsmasq = Service()
        self.dnsmasq.name = 'mcloud_dnsmasq'
        self.dnsmasq.image_builder = InlineDockerfileImageBuilder(source="""
        FROM ubuntu:14.04
        RUN apt-get update && apt-get install -y dnsmasq dnsutils && apt-get clean
        CMD dnsmasq -k --server=/mcloud.lh/%s#%s --server=8.8.8.8 -u root

        """ % (self.settings.dns_ip, self.settings.dns_port))
        self.dnsmasq.ports = [
            '53/tcp:%s_53' % self.settings.dns_ip,
            '53/udp:%s_53' % self.settings.dns_ip,
        ]

        yield self.dnsmasq.create()
        self.app_controller.mark_internal(self.dnsmasq.id)

        yield self.dnsmasq.restart()

        with open('/etc/resolv.conf', 'w+') as f:
            f.write('nameserver %s\n' % self.settings.dns_ip)
            f.write('nameserver 8.8.8.8')

        self.eb.on('containers.updated', self.containers_updated)
        log.msg('Dns plugin started')
        self.containers_updated()

    @inlineCallbacks
    def containers_updated(self, *args, **kwargs):
        data = yield self.app_controller.list()
        self.dump(data)