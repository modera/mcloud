from twisted.internet import reactor
import txredisapi as redis

class myProtocol(redis.SubscriberProtocol):
    def connectionMade(self):
        print "waiting for messages..."
        print "use the redis client to send messages:"
        print "$ redis-cli publish zz test"
        print "$ redis-cli publish foo.bar hello world"
        self.subscribe("zz")
        self.psubscribe("foo.*")
        #reactor.callLater(10, self.unsubscribe, "zz")
        #reactor.callLater(15, self.punsubscribe, "foo.*")

        # self.continueTrying = False
        # self.transport.loseConnection()

    def messageReceived(self, pattern, channel, message):
        print "pattern=%s, channel=%s message=%s" % (pattern, channel, message)

    def connectionLost(self, reason):
        print "lost connection:", reason


class myFactory(redis.SubscriberFactory):
    # SubscriberFactory is a wapper for the ReconnectingClientFactory
    maxDelay = 120
    continueTrying = True
    protocol = myProtocol


reactor.connectTCP("127.0.0.1", 6379, myFactory())
reactor.run()