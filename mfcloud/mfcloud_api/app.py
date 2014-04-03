import txredisapi as redis

from twisted.internet.protocol import Factory, Protocol
from twisted.internet import reactor, defer
from twisted.names import dns
from twisted.names import client, server


class Resolver(client.Resolver):
    def lookupAddress(self, name, timeout=None):
        if name.endswith('.local'):

            d = defer.Deferred()

            result = self.server_factory.redis.get("domain:%s" % name)

            def callback(value):
                a = dns.RRHeader(name=name, type=dns.A, ttl=10)
                a.payload = dns.Record_A(value or '127.0.0.7', ttl=10)
                d.callback(([a], [], []))

            result.addCallback(callback)

            return d
        else:
            return self._lookup(name, dns.IN, dns.A, timeout)


class DNSServerFactory(server.DNSServerFactory):

    def __init__(self, authorities=None, caches=None, clients=None, verbose=0):

        resolver = Resolver(servers=[('8.8.8.8', 53)])
        resolver.server_factory = self

        if not clients:
            clients = []

        clients.append(resolver)

        server.DNSServerFactory.__init__(self, authorities, caches, clients, verbose)

    @defer.inlineCallbacks
    def startFactory(self):
        Factory.startFactory(self)

        self.redis = yield redis.Connection()

    def stopFactory(self):
        self.redis.disconnect()

verbosity = 0
factory = DNSServerFactory(verbose=verbosity)

protocol = dns.DNSDatagramProtocol(factory)
factory.noisy = protocol.noisy = verbosity

reactor.listenUDP(53, protocol, interface='0.0.0.0')
reactor.listenTCP(53, factory, interface='0.0.0.0')
reactor.run()