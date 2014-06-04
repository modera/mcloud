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

            d = defer.Deferred()

            result = self.server_factory.redis.hget("domain", name)

            def callback(value):

                a = dns.RRHeader(name=name, type=dns.A, ttl=10)
                address = value or '127.0.0.1'

                logging.debug('Asked for %s -> Resolved to: %s' % (name, address))
                a.payload = dns.Record_A(address, ttl=10)
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
    parser.add_argument('--interface', type=str, default='0.0.0.0', help='ip address')

    args = parser.parse_args()


    ns_line = 'nameserver %s' % args.interface

    with open('/etc/resolv.conf', 'r') as f:
        contents = f.read()
        print contents

    if not ns_line in contents:
        with open('/etc/resolv.conf', 'w') as f:
             f.write('%s\n%s' % (ns_line, contents))

    def run_server(redis):
        verbosity = 0
        factory = DNSServerFactory(verbose=verbosity, prefix=args.prefix)

        protocol = dns.DNSDatagramProtocol(factory)
        factory.noisy = protocol.noisy = verbosity

        def my_config(binder):
            binder.bind(txredisapi.Connection, redis)

        # Configure a shared injector.
        inject.configure(my_config)

        reactor.listenUDP(args.port, protocol, interface=args.interface)
        reactor.listenTCP(args.port, factory, interface=args.interface)


    def timeout():
        print('Can not connect to redis!')
        reactor.stop()

    txtimeout(txredisapi.Connection(dbid=1), 3, timeout).addCallback(run_server)

    root_logger.info('Listening on %s:%s' % (args.interface, args.port))

    reactor.run()


if __name__ == '__main__':
    entry_point()

