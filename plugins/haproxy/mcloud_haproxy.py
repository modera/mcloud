import logging
import datetime
import traceback
from autobahn.twisted.util import sleep
import inject
from mcloud.application import ApplicationController
from mcloud.container import PrebuiltImageBuilder, InlineDockerfileImageBuilder, VirtualFolderImageBuilder
from mcloud.deployment import DeploymentController, IDeploymentPublishListener
from mcloud.events import EventBus
from mcloud.plugin import IMcloudPlugin
from mcloud.plugins import Plugin, PluginInitError
from mcloud.remote import ApiRpcServer
from mcloud.service import Service, IServiceLifecycleListener
import os
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks
from twisted.python import log
from zope.interface import implements

import re

HAPROXY_TPL = """
defaults
        option  dontlognull
        timeout connect 5000
        timeout client 50000
        timeout server 50000


{% if ssl_apps %}
frontend http_ssl_proxy
  mode tcp
  bind 0.0.0.0:443

  tcp-request inspect-delay 5s
  tcp-request content accept if { req_ssl_hello_type 1 }

  {% for app in ssl_apps %}
  {% for domain in app.domains %}
  acl is_ssl_{{ app.name }} req_ssl_sni -i {{ domain }}
  {% endfor %}
  use_backend backend_ssl_{{ app.name }}_cluster if is_ssl_{{ app.name }}
  {% endfor %}

  {% for app in ssl_apps %}
  {% for backend in app.backends %}
  backend {{ backend.name }}_cluster
      mode tcp

      # maximum SSL session ID length is 32 bytes.
      stick-table type binary len 32 size 30k expire 30m

      acl clienthello req_ssl_hello_type 1
      acl serverhello rep_ssl_hello_type 2

      # use tcp content accepts to detects ssl client and server hello.
      tcp-request inspect-delay 5s
      tcp-request content accept if clienthello

      # no timeout on response inspect delay by default.
      tcp-response content accept if serverhello

      stick on payload_lv(43,1) if clienthello

      # Learn on response if server hello.
      stick store-response payload_lv(43,1) if serverhello

      option ssl-hello-chk

      server {{ backend.name }} {{ backend.ip }}:{{ backend.port }} check

  {% endfor %}
  {% endfor %}
{% endif %}

frontend http_proxy
  bind 0.0.0.0:80

  mode    http
  option  httpclose
  option  forwardfor

  {% for app in apps %}
  {% for domain in app.domains %}
  acl is_{{ app.name }} hdr(host) -i {{ domain }}
  {% endfor %}
  use_backend backend_{{ app.name }}_cluster if is_{{ app.name }}
  {% endfor %}

  {% for app in apps %}
  {% for backend in app.backends %}
  backend {{ backend.name }}_cluster
      mode    http
      server {{ backend.name }} {{ backend.ip }}:{{ backend.port }}
  {% endfor %}
  {% endfor %}
"""

from jinja2 import Template

logger = logging.getLogger('mcloud.plugin.haproxy')


class HaproxyPlugin(Plugin):
    implements(IMcloudPlugin, IServiceLifecycleListener, IDeploymentPublishListener)

    eb = inject.attr(EventBus)
    settings = inject.attr('settings')

    rpc_server = inject.attr(ApiRpcServer)

    dep_controller = inject.attr(DeploymentController)
    app_controller = inject.attr(ApplicationController)

    @inlineCallbacks
    def dump(self):
        deployments = {}

        app_list = yield self.app_controller.list()

        for app in app_list:

            if not app['deployment'] in deployments:
                deployments[app['deployment']] = {
                    'apps': [],
                    'ssl_apps': []
                }

            # if not 'web_target' in app or not app['web_target']:
            #     continue

            plain_domains = {app['web_target']: [app['fullname']]}
            ssl_domains = {}

            if app['public_urls']:
                for target in app['public_urls']:

                    if not target['service']:
                        if 'ssl_target' in app and app['ssl_target'] and target['url'].startswith('https://'):
                            if not app['ssl_target'] in ssl_domains:
                                ssl_domains[app['ssl_target']] = []
                            ssl_domains[app['ssl_target']].append(target['url'][8:])

                        if 'web_target' in app and app['web_target'] and not target['url'].startswith('https://'):
                            if not app['web_target'] in plain_domains:
                                plain_domains[app['web_target']] = []
                            plain_domains[app['web_target']].append(target['url'])

                    else:
                        for service in app['services']:

                            if not service['ip']:
                                continue
                            if service['shortname'] == target['service']:

                                if 'port' in target and target['port']:
                                    service['ip'] = service['ip'] + ':' + target['port']

                                if 'send-proxy' in service and service['send-proxy']:
                                    service['ip'] = service['ip'] + '@send-proxy'


                                if target['url'].startswith('https://'):
                                    if not service['ip'] in ssl_domains:
                                        ssl_domains[service['ip']] = []
                                    ssl_domains[service['ip']].append(target['url'][8:])
                                else:
                                    if not service['ip'] in plain_domains:
                                        plain_domains[service['ip']] = []
                                    plain_domains[service['ip']].append(target['url'])


            def format_name(name):
                return re.sub('[\.\-\s]+', '_', str(name))

            if ssl_domains:
                for ip, domains in ssl_domains.items():
                    port = 443
                    if ':' in ip:
                        ip, port = ip.split(':')

                    deployments[app['deployment']]['ssl_apps'].append({
                        'name': '%s_%s_%s' % (app['fullname'], format_name(ip), format_name(port)),
                        'domains': domains,
                        'backends': [{'name': 'backend_ssl_%s_%s_%s' % (app['fullname'], format_name(ip), format_name(port)), 'ip': ip, 'port': port}]
                    })

            for ip, domains in plain_domains.items():
                if ip is None:
                    continue

                port = 80
                if ':' in ip:
                    ip, port = ip.split(':')

                deployments[app['deployment']]['apps'].append({
                    'name': '%s_%s_%s' % (app['fullname'], format_name(ip), format_name(port)),
                    'domains': domains,
                    'backends': [{'name': 'backend_%s_%s_%s' % (app['fullname'], format_name(ip), format_name(port)), 'ip': ip, 'port': port}]
                })

        log.msg('Writing haproxy config')

        defer.returnValue(deployments)

    @inlineCallbacks
    def rebuild_haproxy(self, deployments=None, ticket_id=None):

        # generate new haproxy config
        all_deployments = yield self.dump()

        for deployment_name, config in all_deployments.items():

            # rebuild only needed deployments
            if deployments and not deployment_name in deployments:
                continue

            if ticket_id:
                self.rpc_server.task_progress('Updating haproxy config on deployment %s' % deployment_name, ticket_id)

            deployment = yield self.dep_controller.get(deployment_name)

            haproxy_path = os.path.expanduser('%s/haproxy/%s' % (self.settings.home_dir, deployment_name))
            if not os.path.exists(haproxy_path):
                os.makedirs(haproxy_path)

            template_path = os.path.join(haproxy_path, 'haproxy.tpl')
            haproxy_config_path = os.path.join(haproxy_path, 'haproxy.cfg')

            if not os.path.exists(template_path):
                with open(template_path, 'w+') as f:
                    f.write(HAPROXY_TPL)

            with open(template_path) as f:
                template = Template(f.read())

            config_rendered = template.render(config)

            with open(haproxy_config_path, 'w+') as f:
                f.write(config_rendered)

            haproxy = Service(client=deployment.get_client())
            haproxy.name = 'mcloud_haproxy'
            haproxy.image_builder = VirtualFolderImageBuilder({
                'Dockerfile': """
                    FROM haproxy:1.5
                    ADD haproxy.cfg /usr/local/etc/haproxy/haproxy.cfg

                    """,
                'haproxy.cfg': config_rendered

            })


            haproxy.ports = ['80/tcp:80', '443/tcp:443']
            # haproxy.volumes = [{
            #     'local': haproxy_path,
            #     'remote': '/etc/haproxy'
            # }]

            logger.info('Containers updated: dumping haproxy config.')

            if ticket_id:
                self.rpc_server.task_progress('updated %s - OK' % deployment_name, ticket_id)

            yield haproxy.rebuild()

    @inlineCallbacks
    def on_service_start(self, service, ticket_id=None):
        """
        :param service:
        :type service: mcloud.service.Service
        :return:
        """
        print 'Service start', service
        if service.name != 'mcloud_haproxy' and (service.is_web() or service.is_ssl()):

            app = yield self.app_controller.get(service.app_name)

            if ticket_id:
                self.rpc_server.task_progress('Updating haproxy config', ticket_id)

            deployment = yield app.get_deployment()
            yield self.rebuild_haproxy(deployments=[deployment.name], ticket_id=ticket_id)

    @inlineCallbacks
    def on_domain_publish(self, deployment, domain, ticket_id=None):
        """
        Called when domain is beeing published
        """
        if ticket_id:
            self.rpc_server.task_progress('Updating haproxy config for deployment %s' % deployment.name, ticket_id)

        yield self.rebuild_haproxy(deployments=[deployment.name])

    @inlineCallbacks
    def on_domain_unpublish(self, deployment, domain, ticket_id=None):
        """
        Called when domain is beeing published
        """
        if ticket_id:
            self.rpc_server.task_progress('Updating haproxy config for deployment %s' % deployment.name, ticket_id)

        yield self.rebuild_haproxy(deployments=[deployment.name])

    @inlineCallbacks
    def setup(self):
        yield self.rebuild_haproxy()
