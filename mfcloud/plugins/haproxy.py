import logging
import inject
from mfcloud.application import ApplicationController
from mfcloud.events import EventBus
from mfcloud.plugins import Plugin
import os
from twisted.internet.defer import inlineCallbacks
from twisted.python import log

HAPROXY_TPL = """
global
        log /dev/log    local0
        log /dev/log    local1 notice
        chroot /var/lib/haproxy
        user haproxy
        group haproxy
        daemon

defaults
        log     global
        mode    http
        option  httplog
        option  dontlognull
        contimeout 5000
        clitimeout 50000
        srvtimeout 50000
        errorfile 400 /etc/haproxy/errors/400.http
        errorfile 403 /etc/haproxy/errors/403.http
        errorfile 408 /etc/haproxy/errors/408.http
        errorfile 500 /etc/haproxy/errors/500.http
        errorfile 502 /etc/haproxy/errors/502.http
        errorfile 503 /etc/haproxy/errors/503.http
        errorfile 504 /etc/haproxy/errors/504.http

frontend http_proxy
  bind 0.0.0.0:80

  {% for app in apps %}
  {% for domain in app.domains %}
  acl is_{{ app.name }} hdr_dom(host) -i {{ domain }}{% endfor %}
  use_backend {{ app.name }}_cluster if is_{{ app.name }}
  {% endfor %}

{% for app in apps %}
backend {{ app.name }}_cluster
  {% for backend in app.backends %}server {{ backend.name }} {{ backend.ip }}:{{ backend.port }}{% endfor %}
{% endfor %}
"""

from jinja2 import Template

logger = logging.getLogger('mfcloud.plugin.haproxy')

class HaproxyConfig(object):

    def __init__(self, path, template=None):
        self.template = template
        self.path = path

    def dump(self, apps_list):

        template = self.template

        if not template:
            template = Template(HAPROXY_TPL)

        proxy_apps = []

        for app in apps_list:
            if not app['running']:
                continue

            domains = [app['fullname']]

            if app['public_url']:
                domains.append(app['public_url'])

            proxy_apps.append({
                'name': app['fullname'],
                'domains': domains,
                'backends': [{
                     'name': 'backend_%s' % app['fullname'],
                     'ip': app['web_ip'],
                     'port': 80
                 }]
            })

        with open('/etc/haproxy/haproxy.cfg', 'w') as f:
            f.write(template.render({'apps': proxy_apps}))

        os.system('service haproxy reload')


class HaproxyPlugin(Plugin):
    eb = inject.attr(EventBus)
    app_controller = inject.attr(ApplicationController)

    def __init__(self):
        super(HaproxyPlugin, self).__init__()

        self.eb.on('containers.updated', self.containers_updated)
        self.proxy_config = HaproxyConfig(path='/etc/haproxy/haproxy.cfg')

        logger.info('Haproxy plugin started')

    @inlineCallbacks
    def containers_updated(self):
        logger.info('Containers updated: dumping haproxy config.')
        data = yield self.app_controller.list()
        self.proxy_config.dump(data)
