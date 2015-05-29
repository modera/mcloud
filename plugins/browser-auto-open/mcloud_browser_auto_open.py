import inject
from mcloud.plugin import IMcloudPlugin
from mcloud.plugins import Plugin
from mcloud.remote import ApiRpcServer
from mcloud.service import IServiceLifecycleListener
import os
from twisted.internet.defer import inlineCallbacks
from zope.interface import implements

class BrowserAutoOpenPlugin(Plugin):
    implements(IMcloudPlugin, IServiceLifecycleListener)

    rpc_server = inject.attr(ApiRpcServer)
    dns_search_suffix = inject.attr('dns-search-suffix')

    @inlineCallbacks
    def on_service_start(self, service, ticket_id=None):
        if service.is_web():
            domain = '%s.%s' % (service.app_name, self.dns_search_suffix)
            if ticket_id:
                yield self.rpc_server.task_progress('Launching web-browser: %s' % domain, ticket_id)

            os.system('sensible-browser %s' % domain)


    @inlineCallbacks
    def setup(self):
        yield None
