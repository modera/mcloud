import logging
import sys
import netifaces

import inject
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.protocol import Factory
import txredisapi
from twisted.python import log
from mcloud.plugins.internal_api import InternalApiPlugin
from mcloud.plugins.metrics import MetricsPlugin
from mcloud.util import txtimeout


log.startLogging(sys.stdout)

Factory.noisy = False


def get_argparser():
    import argparse

    parser = argparse.ArgumentParser(description='Mcloud rpc server')
    parser.add_argument('--port', type=int, default=7080, help='port number')
    parser.add_argument('--file-port', type=int, default=7081, help='File transfer port number')
    parser.add_argument('--haproxy', default=False, action='store_true', help='Update haproxy config')
    # parser.add_argument('--dns', type=bool, default=True, action='store_true', help='Start dns server')
    # parser.add_argument('--events', type=bool, default=True, action='store_true', help='Start dns server')
    parser.add_argument('--dns-server-ip', type=str, default=None, help='Dns server to use in containers')
    parser.add_argument('--dns-search-suffix', type=str, default='mcloud.lh', help='Dns suffix to use')
    parser.add_argument('--host-ip', type=str, default=None, help='Proxy destination for non-local traffic')
    parser.add_argument('--interface', type=str, default='0.0.0.0', help='ip address')
    #parser.add_argument('--zmq-bind', type=str, default='tcp://0.0.0.0:5555', help='ip address')
    return parser


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

    rpc_interface = args.interface
    rpc_port = args.port
    file_port = args.file_port

    if not args.dns_server_ip:
        dns_server_ip = netifaces.ifaddresses('docker0')[netifaces.AF_INET][0]['addr']
    else:
        dns_server_ip = args.dns_server_ip

    dns_prefix = args.dns_search_suffix

    from confire import Configuration

    class SslConfiguration(Configuration):
        enabled = False
        key = '/etc/mcloud/ssl.key'
        cert = '/etc/mcloud/ssl.crt'

    class MyAppConfiguration(Configuration):

        CONF_PATHS = [
            '/etc/mcloud/mcloud-server.yml',
            # os.path.expanduser('~/.myapp.yaml'),
            # os.path.abspath('conf/myapp.yaml')
        ]

        haproxy = False

        ssl = SslConfiguration()

    settings = MyAppConfiguration.load()
    
    @inlineCallbacks
    def run_server(redis):

        from mcloud.dns_resolver import listen_dns
        from mcloud.events import EventBus
        from mcloud.plugins.dns import DnsPlugin
        from mcloud.plugins.haproxy import HaproxyPlugin
        from mcloud.plugins.monitor import DockerMonitorPlugin
        from mcloud.txdocker import IDockerClient, DockerTwistedClient
        from mcloud.remote import ApiRpcServer, Server
        from mcloud.tasks import TaskService

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

        log.msg('Starting rpc listener on port %d' % rpc_port)
        server = Server(port=rpc_port)
        server.bind()

        log.msg('Dumping resolv conf')

        # dns
        # dump_resolv_conf(dns_server_ip)

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

        InternalApiPlugin()

        log.msg('Listen dns on ip %s:53' % dns_server_ip)
        listen_dns(dns_prefix, dns_server_ip, 7053)

        log.msg('Listen metrics')
        MetricsPlugin()

        log.msg('Started.')

    def timeout():
        print('Can not connect to redis!')
        reactor.stop()

    txtimeout(txredisapi.Connection(dbid=1), 3, timeout).addCallback(run_server)

    reactor.run()


if __name__ == '__main__':
    entry_point()