import logging
import sys
import inject
from mfcloud.util import txtimeout

from twisted.internet.protocol import Factory, Protocol
from twisted.internet import reactor, defer
from twisted.names import dns
from twisted.names import client, server
import txredisapi


class Resolver(client.Resolver):
    """

    """

    def __init__(self, resolv=None, servers=None, timeout=(1, 3, 11, 45), reactor=None, prefix=None):
        client.Resolver.__init__(self, resolv, servers, timeout, reactor)

        self.prefix = prefix


    def lookupAddress(self, name, timeout=None):
        if name.endswith('.%s' % self.prefix):

            if name == '%s.%s' % ('_dns', self.prefix):
                value = '127.0.1.7'
                a = dns.RRHeader(name=name, type=dns.A, ttl=10)

                logging.debug('Asked for %s -> Resolved to: %s' % (name, value))
                a.payload = dns.Record_A(value, ttl=10)

                return defer.succeed(([a], [], []))

            d = defer.Deferred()

            result = self.server_factory.redis.hget("domain", name)

            def callback(value):

                if not value or value == 'None':
                    d.callback(([], [], []))
                else:
                    a = dns.RRHeader(name=name, type=dns.A, ttl=10)

                    logging.debug('Asked for %s -> Resolved to: %s' % (name, value))
                    a.payload = dns.Record_A(value, ttl=10)
                    d.callback(([a], [], []))

            result.addCallback(callback)

            return d
        else:
            return self._lookup(name, dns.IN, dns.A, timeout)


class DNSServerFactory(server.DNSServerFactory):
    redis = inject.attr(txredisapi.Connection)

    def __init__(self, authorities=None, caches=None, clients=None, prefix=None, verbose=0):
        resolver = Resolver(servers=[('8.8.8.8', 53)], prefix=prefix)
        resolver.server_factory = self

        if not clients:
            clients = []

        clients.append(resolver)

        server.DNSServerFactory.__init__(self, authorities, caches, clients, verbose)


    def stopFactory(self):
        self.redis.disconnect()


def dump_resolv_conf(dns_server_ip):
    ns_line = 'nameserver %s' % dns_server_ip
    with open('/etc/resolv.conf', 'r') as f:
        contents = f.read()
    if not ns_line in contents:
        with open('/etc/resolv.conf', 'w') as f:
            f.write('%s\n%s' % (ns_line, contents))


def listen_dns(dns_prefix, dns_server_ip, dns_port):
    verbosity = 0
    factory = DNSServerFactory(verbose=verbosity, prefix=dns_prefix)
    protocol = dns.DNSDatagramProtocol(factory)
    factory.noisy = protocol.noisy = verbosity

    reactor.listenUDP(dns_port, protocol, interface=dns_server_ip)
    reactor.listenTCP(dns_port, factory, interface=dns_server_ip)


def entry_point():
    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(logging.Formatter())
    console_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG)
    root_logger.debug('Logger initialized')

    import argparse

    parser = argparse.ArgumentParser(description='Dns resolver')

    parser.add_argument('--port', type=int, default='53', help='port number')
    parser.add_argument('--prefix', type=str, default='mfcloud.lh', help='Local domain prefix')
    parser.add_argument('--interface', type=str, default='172.17.42.1', help='ip address')

    args = parser.parse_args()

    dns_server_ip = args.interface
    dns_prefix = args.prefix
    dns_port = args.port

    def run_server(redis):
        def my_config(binder):
            binder.bind(txredisapi.Connection, redis)

        # Configure a shared injector.
        inject.configure(my_config)

        #dump_resolv_conf(dns_server_ip)
        listen_dns(dns_prefix, dns_server_ip, dns_port)


    def timeout():
        print('Can not connect to redis!')
        reactor.stop()

    txtimeout(txredisapi.Connection(dbid=1), 3, timeout).addCallback(run_server)

    root_logger.info('Listening on %s:%s' % (dns_server_ip, args.port))

    reactor.run()


if __name__ == '__main__':
    entry_point()

