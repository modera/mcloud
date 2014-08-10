import logging
import sys

import inject
from mfcloud.plugins.datadog import DatadogPlugin
from mfcloud.plugins.hosts import HostsPlugin

from mfcloud.util import txtimeout
import os
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
import txredisapi

from twisted.python import log
log.startLogging(sys.stdout)


def get_argparser():
    import argparse

    parser = argparse.ArgumentParser(description='Mfcloud rpc server')
    parser.add_argument('--port', type=int, default=7080, help='port number')
    parser.add_argument('--haproxy', default=False, action='store_true', help='Update haproxy config')
    # parser.add_argument('--dns', type=bool, default=True, action='store_true', help='Start dns server')
    # parser.add_argument('--events', type=bool, default=True, action='store_true', help='Start dns server')
    parser.add_argument('--dns-server-ip', type=str, default='172.17.42.1', help='Dns server to use in containers')
    parser.add_argument('--dns-search-suffix', type=str, default='mfcloud.lh', help='Dns suffix to use')
    parser.add_argument('--host-ip', type=str, default=None, help='Proxy destination for non-local traffic')
    parser.add_argument('--interface', type=str, default='0.0.0.0', help='ip address')
    #parser.add_argument('--zmq-bind', type=str, default='tcp://0.0.0.0:5555', help='ip address')
    return parser


def entry_point():

    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(logging.Formatter(fmt='[%(asctime)s][%(levelname)s][%(name)s] %(message)s'))
    console_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG)
    log.msg('Logger initialized')

    parser = get_argparser()

    args = parser.parse_args()

    rpc_interface = args.interface
    rpc_port = args.port
    dns_server_ip = args.dns_server_ip
    dns_prefix = args.dns_search_suffix

    from confire import Configuration
    from confire import environ_setting

    class SslConfiguration(Configuration):
        enabled = False
        key = '/etc/mfcloud/ssl.key'
        cert = '/etc/mfcloud/ssl.crt'

    class MyAppConfiguration(Configuration):

        CONF_PATHS = [
            '/etc/mfcloud/mfcloud-server.yml',
            # os.path.expanduser('~/.myapp.yaml'),
            # os.path.abspath('conf/myapp.yaml')
        ]

        haproxy = False

        ssl = SslConfiguration()

    settings = MyAppConfiguration.load()
    
    @inlineCallbacks
    def run_server(redis):
        from mfcloud.dns_resolver import listen_dns, dump_resolv_conf
        from mfcloud.events import EventBus
        from mfcloud.plugins.dns import DnsPlugin
        from mfcloud.plugins.haproxy import HaproxyPlugin
        from mfcloud.plugins.monitor import DockerMonitorPlugin
        from mfcloud.txdocker import IDockerClient, DockerTwistedClient
        from mfcloud.remote import ApiRpcServer, Server
        from mfcloud.tasks import TaskService

        log.msg('Running server')

        eb = EventBus(redis)
        log.msg('Connecting event bus')
        yield eb.connect()

        log.msg('Configuring injector.')



        def my_config(binder):
            binder.bind(txredisapi.Connection, redis)
            binder.bind(EventBus, eb)
            #binder.bind(IDockerClient, DockerTwistedClient(url='http://127.0.0.1:4243'))
            binder.bind(IDockerClient, DockerTwistedClient())

            binder.bind('settings', settings)
            binder.bind('dns-server', dns_server_ip)
            binder.bind('dns-search-suffix', dns_prefix)

        # Configure a shared injector.
        inject.configure(my_config)

        api = inject.instance(ApiRpcServer)
        tasks = inject.instance(TaskService)
        api.tasks = tasks.collect_tasks()


        log.msg('Starting rpc listener')
        server = Server(port=rpc_port)
        server.bind()

        log.msg('Dumping resolv conf')

        # dns
        dump_resolv_conf(dns_server_ip)

        if settings.haproxy or args.haproxy:
            log.msg('Haproxy plugin')
            HaproxyPlugin()

        # log.msg('Datadog plugin')
        # DatadogPlugin()

        log.msg('Monitor plugin')
        DockerMonitorPlugin()


        log.msg('Dns plugin')
        DnsPlugin()

        # HostsPlugin()

        log.msg('Listen dns')
        listen_dns(dns_prefix, dns_server_ip, 53)

        log.msg('Started.')

    def timeout():
        print('Can not connect to redis!')
        reactor.stop()

    txtimeout(txredisapi.Connection(dbid=1), 3, timeout).addCallback(run_server)

    reactor.run()


if __name__ == '__main__':
    entry_point()