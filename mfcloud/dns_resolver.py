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

    def lookupAddress(self, name, timeout=None):
        if name.endswith('.local'):

            d = defer.Deferred()

            print name
            result = self.server_factory.redis.hget("domain", name)

            def callback(value):
                print value
                a = dns.RRHeader(name=name, type=dns.A, ttl=10)
                a.payload = dns.Record_A(value or '127.0.0.1', ttl=10)
                d.callback(([a], [], []))

            result.addCallback(callback)

            return d
        else:
            return self._lookup(name, dns.IN, dns.A, timeout)

class DNSServerFactory(server.DNSServerFactory):

    redis = inject.attr(txredisapi.Connection)

    def __init__(self, authorities=None, caches=None, clients=None, verbose=0):

        resolver = Resolver(servers=[('8.8.8.8', 53)])
        resolver.server_factory = self

        if not clients:
            clients = []

        clients.append(resolver)

        server.DNSServerFactory.__init__(self, authorities, caches, clients, verbose)


    def stopFactory(self):
        self.redis.disconnect()

if __name__ == '__main__':

    def run_server(redis):
        verbosity = 0
        factory = DNSServerFactory(verbose=verbosity)

        protocol = dns.DNSDatagramProtocol(factory)
        factory.noisy = protocol.noisy = verbosity

        def my_config(binder):
            binder.bind(txredisapi.Connection, redis)

        # Configure a shared injector.
        inject.configure(my_config)

        reactor.listenUDP(53, protocol, interface='172.17.42.1')
        reactor.listenTCP(53, factory, interface='172.17.42.1')



    def timeout():
        print('Can not connect to redis!')
        reactor.stop()

    txtimeout(txredisapi.Connection(dbid=1), 3, timeout).addCallback(run_server)

    reactor.run()