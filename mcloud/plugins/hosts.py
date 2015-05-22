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


class HostsPlugin(Plugin):
    implements(IMcloudPlugin, IServiceBuilder)

    eb = inject.attr(EventBus)
    app_controller = inject.attr(ApplicationController)
    redis = inject.attr(txredisapi.Connection)


    @inlineCallbacks
    def configure_container_on_start(self, service, config):
        if service.app_name:
            from mcloud.application import ApplicationController
            app_controller = inject.instance(ApplicationController)

            ip_list = yield app_controller.ip_list()

            if service.app_name in ip_list and len(ip_list[service.app_name]) > 0:
                config['ExtraHosts'] = ['%s:%s' % x for x in ip_list[service.app_name].items()]

    #@inlineCallbacks
    # def dump(self, apps_list):
    #     for app in apps_list:
    #
    #         containers = {}
    #
    #         for service in app['services']:
    #             if service['ip']:
    #                 containers[service['shortname']] = service['ip']
    #
    #         if containers:
    #             for service in app['services']:
    #                 if service['hosts_path']:
    #                     prepend = ''
    #                     with open(service['hosts_path'], 'r') as f:
    #                         contents = f.read()
    #
    #                         for name, ip in containers.items():
    #                             if name == service['shortname']:
    #                                 continue
    #                             hs_line = '%s\t%s\n' % (ip, name)
    #
    #                             if not hs_line in contents:
    #                                 prepend += hs_line
    #
    #                     if prepend:
    #                         with open(service['hosts_path'], 'w') as f:
    #                             f.write('%s\n%s' % (prepend, contents))
    #
    #                 log.msg('*********** Hosts for %s: %s' % (service['name'], str(containers)))


    # @inlineCallbacks
    def setup(self):
        # self.eb.on('containers.updated', self.containers_updated)

        log.msg('Hosts plugin started')



        # yield self.containers_updated()

    # @inlineCallbacks
    # def containers_updated(self, *args, **kwargs):
    #     log.msg('Containers updated: dumping haproxy config.')
    #
    #     data = yield self.app_controller.list()
    #     self.dump(data)