
import json
import logging
import sys
import inject
from mfcloud.util import txtimeout
import os
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
import txredisapi
from txzmq import ZmqFactory, ZmqEndpoint, ZmqSubConnection

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

from jinja2 import Environment as JinjaEnv, StrictUndefined, Template


class DnsConfig(object):

    redis = inject.attr(txredisapi.Connection)

    def dump(self, apps_list):
        apps = {}

        for app in apps_list:
            if not app['running']:
                continue

            for service in app['services']:
                apps[service['fullname']] = service['ip']

            if app['web_service']:
                apps[app['fullname']] = app['web_ip']

            if app['public_url']:
                apps[app['public_url']] = app['web_ip']

        logging.info('Installing new app list: %s' % str(apps))

        if len(apps) > 1:
            return self.redis.hmset('domain', apps)
        elif len(apps) == 1:
            return self.redis.hset('domain', apps.keys()[0], apps.values()[0])


class HaproxyConfig(object):

    def __init__(self, path, template=None, internal_suffix='mfcloud.lh'):
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


def listen_events(zf2, endpoint, need_haproxy=False):
    proxy_config = HaproxyConfig(path='/etc/haproxy/haproxy.cfg')
    dns_config = DnsConfig()

    logging.info('Start listening on container updates.')

    def on_message(message, tag):
        print('event boooo!')
        if tag == 'event-containers-updated':
            data = json.loads(message)
            dns_config.dump(data['apps'])

            if need_haproxy:
                proxy_config.dump(data['apps'])

    subscribe_con = ZmqSubConnection(zf2, ZmqEndpoint('connect', endpoint))
    subscribe_con.subscribe("")
    subscribe_con.gotMessage = on_message


def entry_point():

    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(logging.Formatter())
    console_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG)
    root_logger.debug('Logger initialized')

    import argparse

    parser = argparse.ArgumentParser(description='Websocket server')
    parser.add_argument('--endpoint', type=str, default=['tcp://127.0.0.1:5555'], nargs='+', help='ip address')
    args = parser.parse_args()



    def run_server(redis):
        zf2 = ZmqFactory()
        listen_events(zf2, args.endpoint)

        def my_config(binder):
            binder.bind(txredisapi.Connection, redis)

        # Configure a shared injector.
        inject.configure(my_config)

    def timeout():
        print('Can not connect to redis!')
        reactor.stop()

    txtimeout(txredisapi.Connection(dbid=1), 3, timeout).addCallback(run_server)



    reactor.run()

if __name__ == '__main__':
    entry_point()