from mcloud.plugin import IMcloudPlugin
from mcloud.plugins import Plugin
from mcloud.service import IServiceBuilder
from zope.interface import implements


class SimplePublishPlugin(Plugin):
    implements(IMcloudPlugin, IServiceBuilder)

    def configure_container_on_create(self, service, config):
        if service.is_web():

            if not 'PortBindings' in config:
                config['PortBindings'] = {}

            if not 'ExposedPorts' in config:
                config['ExposedPorts'] = {}

            config['PortBindings']['%s/tcp' % service.get_web_port()] = [
                {
                    "HostIp": "0.0.0.0",
                    "HostPort": "80"
                }
            ]

            config['ExposedPorts'] = {'%s/tcp' % service.get_web_port(): {}}

    def configure_container_on_start(self, service, config):

        self.configure_container_on_create(service, config)

    def setup(self):
        pass