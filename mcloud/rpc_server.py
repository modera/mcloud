import logging
import sys
import netifaces
from traceback import print_tb
import traceback

import inject
from mcloud.plugin import IMcloudPlugin
import pkg_resources
from twisted.internet import reactor
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

            # binder.bind('dns-server', netifaces.ifaddresses('docker0')[netifaces.AF_INET][0]['addr'])
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

        try:
            # load plugins
            for ep in pkg_resources.iter_entry_points(group='mcloud_plugins'):
                plugin_class = ep.load()

                log.msg('=' * 80)
                log.msg('Loading plugin %s' % plugin_class)
                log.msg('-' * 80)

                yield verifyClass(IMcloudPlugin, plugin_class)

                plugin = plugin_class()

                yield plugin.setup()
                plugins_loaded.append(plugin)

                print "Loaded %s - OK" % plugin_class

        except Exception as e:
            print '!-' * 40
            print e.__class__.__name__
            print e
            print(traceback.format_exc())
            print '!-' * 40

            reactor.stop()

            log.msg('=' * 80)


        log.msg('-' * 80)
        log.msg('All plugins loaded.')
        log.msg('=' * 80)


        # HostsPlugin()

        # InternalApiPlugin()

        # log.msg('Listen dns on ip %s:53' % settings.dns_ip)
        # listen_dns(settings.dns_search_suffix, settings.dns_ip, settings.dns_port)

        # if settings.web:
        #     log.msg('Start internal web server')
        #     reactor.listenTCP(8080, Site(mcloud_web()), interface=dns_server_ip)
        #     listen_web(settings)

        # log.msg('Listen metrics')
        # MetricsPlugin()

        log.msg('Started.')

    def timeout():
        print('Can not connect to redis!')
        reactor.stop()

    print '*******'
    print 'Connecting redis:'
    print settings.redis
    print '*******'

    txtimeout(txredisapi.Connection(
        dbid=settings.redis.dbid,
        host=settings.redis.host,
        port=settings.redis.port,
        password=settings.redis.password
    ), settings.redis.timeout, timeout).addCallback(run_server)

    reactor.run()


if __name__ == '__main__':
    entry_point()