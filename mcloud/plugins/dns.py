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
import logging
import inject
from mcloud.application import ApplicationController
from mcloud.events import EventBus
from mcloud.plugin import IMcloudPlugin
from mcloud.plugins import Plugin
from mcloud.service import IServiceBuilder
from twisted.internet.defer import inlineCallbacks
import txredisapi
from twisted.python import log
from zope.interface import implements


class DnsPlugin(Plugin):
    implements(IMcloudPlugin, IServiceBuilder)


    eb = inject.attr(EventBus)
    app_controller = inject.attr(ApplicationController)
    redis = inject.attr(txredisapi.Connection)
    settings = inject.attr('settings')
    host_ip = inject.attr('host-ip')
    dns_search_suffix = inject.attr('dns-search-suffix')
    """ @var McloudConfiguration """

    @inlineCallbacks
    def dump(self, apps_list):
        apps = {
            'mcloud.lh': self.host_ip
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

        log.msg('Restarting dnsmasq')

        # extra options
        cmd = []
        for url, ip in apps.items():
            cmd.append('--host-record=%s,%s' % (url, ip))


        self.dnsmasq = Service()
        self.dnsmasq.name = 'mcloud_dnsmasq'
        self.dnsmasq.image_builder = InlineDockerfileImageBuilder(source="""
        FROM ubuntu:14.04
        RUN apt-get update && apt-get install -y dnsmasq dnsutils && apt-get clean
        CMD dnsmasq -k %s --server=8.8.8.8 -u root
        """ % ' '.join(cmd))

        self.dnsmasq.ports = [
            '53/tcp:%s_53' % self.settings.dns_ip,
            '53/udp:%s_53' % self.settings.dns_ip,
        ]

        yield self.dnsmasq.create()
        self.app_controller.mark_internal(self.dnsmasq.id)

        yield self.dnsmasq.rebuild()

        # with open('/etc/resolv.conf', 'w+') as f:
        #     f.write('nameserver %s\n' % self.host_ip)
        #     f.write('nameserver 8.8.8.8')




    def configure_container_on_create(self, service, config):
        pass


    @inlineCallbacks
    def configure_container_on_start(self, service, config):
        pass
        # config.update({
        #     "Dns": [self.host_ip],
        #     "DnsSearch": '%s.%s' % (service.app_name, self.dns_search_suffix)
        # })


    @inlineCallbacks
    def setup(self):
        pass
        # self.eb.on('containers.updated', self.containers_updated)
        # log.msg('Dns plugin started')
        #
        # yield self.containers_updated()

    @inlineCallbacks
    def containers_updated(self, *args, **kwargs):
        data = yield self.app_controller.list()
        self.dump(data)
