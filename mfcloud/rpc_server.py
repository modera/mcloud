import json
import logging
import sys
import netifaces
import inject
from mfcloud.dns_resolver import listen_dns, dump_resolv_conf
from mfcloud.haproxy import listen_events
from mfcloud.monitor import DockerMonitor
from mfcloud.tasks import TaskService
from mfcloud.txdocker import IDockerClient, DockerTwistedClient
from mfcloud.util import txtimeout
from twisted.internet import defer, reactor
from twisted.web import xmlrpc, server
import txredisapi
from txzmq import ZmqFactory, ZmqEndpoint, ZmqPubConnection


logger = logging.getLogger('mfcloud.server')

class ApiRpcServer(xmlrpc.XMLRPC):
    redis = inject.attr(txredisapi.Connection)
    zmq = inject.attr(ZmqPubConnection)

    def __init__(self, allowNone=False, useDateTime=False):
        xmlrpc.XMLRPC.__init__(self, allowNone, useDateTime)

        self.tasks = {}

    def task_completed(self, result, ticket_id):
        self.zmq.publish(json.dumps(result), 'task-completed-%s' % ticket_id)

        #print 'Result is %s' % result
        return defer.DeferredList([
            self.redis.set('mfcloud-ticket-%s-completed' % ticket_id, 1),
            self.redis.set('mfcloud-ticket-%s-result' % ticket_id, json.dumps(result))
        ])

    def task_failed(self, error, ticket_id):
        print 'Failure: <%s> %s' % (error.type, error.getErrorMessage())
        print error.printTraceback()
        self.zmq.publish("Failed: <%s> %s" % (error.type, error.getErrorMessage()), 'task-failed-%s' % ticket_id)

    def xmlrpc_task_start(self, task_name, *args, **kwargs):
        """
        Return all passed args.
        """

        d = self.redis.incr('mfcloud-ticket-id')

        def process_task_id(ticket_id):
            if not task_name in self.tasks:
                raise ValueError('No such task: %s' % task_name)
            task_defered = self.tasks[task_name](ticket_id, *args, **kwargs)

            task_defered.addCallback(self.task_completed, ticket_id)
            task_defered.addErrback(self.task_failed, ticket_id)

            return {
                'ticket_id': ticket_id
            }

        def on_error(error):
            return xmlrpc.Fault(1, "Task execution failed: <%s> %s" % (error.type, error.getErrorMessage()))

        d.addCallback(process_task_id)
        d.addErrback(on_error)

        return d

    def xmlrpc_is_completed(self, ticket_id):
        d = self.redis.get('mfcloud-ticket-%s-completed' % ticket_id)

        def on_result(result):
            return result == 1

        d.addCallback(on_result)
        return d

    def xmlrpc_get_result(self, ticket_id):
        d = self.redis.get('mfcloud-ticket-%s-result' % ticket_id)
        d.addCallback(lambda result: json.loads(result))
        return d


def get_argparser():
    import argparse

    parser = argparse.ArgumentParser(description='Dns resolver')
    parser.add_argument('--port', type=int, default=7080, help='port number')
    parser.add_argument('--haproxy', default=False, action='store_true', help='Update haproxy config')
    # parser.add_argument('--dns', type=bool, default=True, action='store_true', help='Start dns server')
    # parser.add_argument('--events', type=bool, default=True, action='store_true', help='Start dns server')
    parser.add_argument('--docker-uri', type=str, default='unix://var/run/docker.sock/', help='Docker connection uri')
    parser.add_argument('--dns-server-ip', type=str, default=None, help='Dns server to use in containers')
    parser.add_argument('--dns-search-suffix', type=str, default='mfcloud.lh', help='Dns suffix to use')
    parser.add_argument('--host-ip', type=str, default=None, help='Proxy destination for non-local traffic')
    parser.add_argument('--interface', type=str, default='0.0.0.0', help='ip address')
    parser.add_argument('--zmq-bind', type=str, default='tcp://0.0.0.0:5555', help='ip address')
    return parser


def entry_point():

    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(logging.Formatter())
    console_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG)
    root_logger.debug('Logger initialized')



    parser = get_argparser()

    args = parser.parse_args()

    rpc_interface = args.interface
    rpc_port = args.port
    dns_server_ip = args.dns_server_ip
    dns_prefix = args.dns_search_suffix
    docker_uri = args.docker_uri


    # detect dns server ip
    if not dns_server_ip:
        try:
            dns_server_ip = netifaces.ifaddresses('docker0')[netifaces.AF_INET][0]['addr']
            print('Docker0 ip is: %s assigning dns there' % dns_server_ip)
        except KeyError:
            dns_server_ip = '172.17.42.1'
            print('Can not find docker0 ip. Setting default %s' % dns_server_ip)
    else:
        print('Using provided ip for dns: %s' % dns_server_ip)

    def listen_rpc():
        tasks = TaskService()
        api = ApiRpcServer()
        tasks.register(api)
        monitor = DockerMonitor()
        monitor.start()
        reactor.listenTCP(rpc_port, server.Site(api), interface=rpc_interface)

    def run_server(redis):

        zf = ZmqFactory()
        e = ZmqEndpoint('bind', args.zmq_bind)
        s = ZmqPubConnection(zf, e)

        def my_config(binder):
            binder.bind(txredisapi.Connection, redis)
            binder.bind(ZmqPubConnection, s)
            binder.bind(IDockerClient, DockerTwistedClient())

            binder.bind('dns-server', dns_server_ip)
            binder.bind('docker-uri', docker_uri)
            binder.bind('dns-search-suffix', dns_prefix)
            #binder.bind('host-ip', args.host_ip)

        # Configure a shared injector.
        inject.configure(my_config)

        # rpc
        listen_rpc()

        # dns
        dump_resolv_conf(dns_server_ip)
        listen_dns(dns_prefix, dns_server_ip, 53)

        # events
        listen_events(zf, args.zmq_bind, args.haproxy)

    def timeout():
        print('Can not connect to redis!')
        reactor.stop()

    txtimeout(txredisapi.Connection(dbid=1), 3, timeout).addCallback(run_server)

    reactor.run()


if __name__ == '__main__':
    entry_point()