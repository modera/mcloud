from cratis.cli import load_env
import os

from mcloud.django.startup import init_django
from pkg_resources import resource_filename



init_django()


import logging
import sys
import netifaces
import traceback

import inject
from mcloud.deployment import DeploymentController
from mcloud.plugin import IMcloudPlugin
import pkg_resources
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks
from twisted.internet.protocol import Factory
import txredisapi
from twisted.python import log
from mcloud.util import txtimeout
from zope.interface.verify import verifyClass


log.startLogging(sys.stdout)

Factory.noisy = False


def get_argparser():
    import argparse

    parser = argparse.ArgumentParser(description='Mcloud rpc server')
    parser.add_argument('--config', default='/etc/mcloud/mcloud-server.yml', help='Config file path')
    parser.add_argument('--import-redis', default=False, action='store_true', help='Import redis data and exit')
    parser.add_argument('--no-ssl', default=False, action='store_true', help='Disable ssl')

    return parser


from confire import Configuration

class SslConfiguration(Configuration):
    enabled = False
    key = '/etc/mcloud/server.key'
    cert = '/etc/mcloud/server.crt'
    ca = '/etc/mcloud/ca.crt'

class RedisConfiguration(Configuration):
    host = 'localhost'
    port = 6379
    password = None
    dbid = 1
    timeout = 3

class McloudConfiguration(Configuration):
    haproxy = False
    web = True

    dns_ip = None
    dns_port = 7053

    websocket_ip = '0.0.0.0'
    websocket_port = 7080

    dns_search_suffix = 'mcloud.lh'

    ssl = SslConfiguration()

    redis = RedisConfiguration()

    home_dir = '/root/.mcloud'
    btrfs = False
    demo_mode = False


def entry_point():

    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(logging.Formatter(fmt='[%(asctime)s][%(levelname)s][%(name)s] %(message)s'))
    console_handler.setLevel(logging.ERROR)

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.ERROR)
    log.msg('Logger initialized')

    parser = get_argparser()
    args = parser.parse_args()


    class _McloudConfiguration(McloudConfiguration):
        CONF_PATHS = [args.config]

    settings = _McloudConfiguration.load()

    if args.no_ssl:
        settings.ssl.enabled = False

    def resolve_host_ip():

        if 'docker0' in netifaces.interfaces():
            return netifaces.ifaddresses('docker0')[netifaces.AF_INET][0]['addr']
        else:
            import netinfo
            host_ip = None
            for route in netinfo.get_routes():
                if route['dest'] == '0.0.0.0':  # default route
                    host_ip = route['gateway']
            if not host_ip:
                reactor.stop()
                print('ERROR: Can not get default route - can not connect to Docker')
            return host_ip

    @inlineCallbacks
    def run_server(redis):

        from mcloud.events import EventBus
        from mcloud.remote import ApiRpcServer, Server
        from mcloud.tasks import TaskService

        log.msg('Running server')

        eb = EventBus(redis)
        log.msg('Connecting event bus')
        yield eb.connect()

        log.msg('Configuring injector.')

        plugins_loaded = []


        def my_config(binder):
            binder.bind(txredisapi.Connection, redis)
            binder.bind(EventBus, eb)

            binder.bind('settings', settings)

            binder.bind('host-ip', resolve_host_ip())
            binder.bind('dns-search-suffix', settings.dns_search_suffix)
            binder.bind('plugins', plugins_loaded)

        # Configure a shared injector.
        inject.configure(my_config)

        api = inject.instance(ApiRpcServer)
        tasks = inject.instance(TaskService)
        api.tasks = tasks.collect_tasks()

        log.msg('Starting rpc listener on port %d' % settings.websocket_port)
        server = Server(port=settings.websocket_port)
        server.bind()

        from .django.core.management import call_command

        call_command('collectstatic', interactive=False)

        call_command('syncdb')
        call_command('migrate', verbosity=3, interactive=False)

        # load plugins
        for ep in pkg_resources.iter_entry_points(group='mcloud_plugins'):
            try:

                plugin_class = ep.load()

                log.msg('=' * 80)
                log.msg('Loading plugin %s' % plugin_class)
                log.msg('-' * 80)

                yield verifyClass(IMcloudPlugin, plugin_class)

                plugin = plugin_class()

                yield plugin.setup()
                plugins_loaded.append(plugin)

                print("Loaded %s - OK" % plugin_class)

            except Exception as e:
                print('!-' * 40)
                print(e.__class__.__name__)
                print(e)
                print((traceback.format_exc()))
                print('!-' * 40)

                # reactor.stop()

                log.msg('=' * 80)

        log.msg('-' * 80)
        log.msg('All plugins loaded.')
        log.msg('=' * 80)

        deployment_controller = inject.instance(DeploymentController)
        yield deployment_controller.configure_docker_machine()

        log.msg('Started.')


    def timeout():
        print('Can not connect to redis!')
        reactor.stop()

    print('*******')
    print('Connecting redis:')
    print(settings.redis)
    print('*******')

    txtimeout(txredisapi.Connection(
        dbid=settings.redis.dbid,
        host=settings.redis.host,
        port=settings.redis.port,
        password=settings.redis.password
    ), settings.redis.timeout, timeout).addCallback(run_server)

    reactor.run()


if __name__ == '__main__':
    entry_point()