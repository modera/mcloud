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
from zope.interface import implements, implementer


@implementer(IMcloudPlugin, IServiceBuilder)
class HostsPlugin(Plugin):


    eb = inject.attr(EventBus)
    app_controller = inject.attr(ApplicationController)
    redis = inject.attr(txredisapi.Connection)


    def configure_container_on_create(self, service, config):
        pass


    @inlineCallbacks
    def configure_container_on_start(self, service, config):
        if service.app_name:
            from mcloud.application import ApplicationController
            app_controller = inject.instance(ApplicationController)

            ip_list = yield app_controller.ip_list()

            if service.app_name in ip_list and len(ip_list[service.app_name]) > 0:
                config['ExtraHosts'] = ['%s:%s' % x for x in ip_list[service.app_name].items()]

    def setup(self):
        log.msg('Hosts plugin started')
