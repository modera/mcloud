import logging
import inject
from mfcloud.application import ApplicationController
from mfcloud.events import EventBus
from mfcloud.plugins import Plugin
from twisted.internet.defer import inlineCallbacks
import txredisapi
from twisted.python import log


class HostsPlugin(Plugin):
    eb = inject.attr(EventBus)
    app_controller = inject.attr(ApplicationController)
    redis = inject.attr(txredisapi.Connection)

    #@inlineCallbacks
    def dump(self, apps_list):
        for app in apps_list:

            containers = {}

            for service in app['services']:
                if service['ip']:
                    containers[service['shortname']] = service['ip']

            if containers:
                for service in app['services']:
                    if service['hosts_path']:
                        prepend = ''
                        with open(service['hosts_path'], 'r') as f:
                            contents = f.read()

                            for name, ip in containers.items():
                                if name == service['shortname']:
                                    continue
                                hs_line = '%s\t%s\n' % (ip, name)

                                if not hs_line in contents:
                                    prepend += hs_line

                        if prepend:
                            with open(service['hosts_path'], 'w') as f:
                                f.write('%s\n%s' % (prepend, contents))

                    log.msg('*********** Hosts for %s: %s' % (service['name'], str(containers)))

    def __init__(self):
        super(HostsPlugin, self).__init__()
        self.eb.on('containers.updated', self.containers_updated)

        log.msg('Hosts plugin started')

        self.containers_updated()

    @inlineCallbacks
    def containers_updated(self, *args, **kwargs):
        log.msg('Containers updated: dumping haproxy config.')

        data = yield self.app_controller.list()
        self.dump(data)