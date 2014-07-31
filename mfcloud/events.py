import json

from twisted.internet import reactor, defer
import txredisapi as redis
from twisted.python import log


class EventBus(object):
    redis = None
    protocol = None

    def __init__(self, redis_connection):
        super(EventBus, self).__init__()
        self.redis = redis_connection

    def fire_event(self, event_name, data=None, *args, **kwargs):
        log.msg('Firing event: %s' % event_name)

        if not data:
            if kwargs:
                data = kwargs
            elif args:
                data = args

        if not isinstance(data, basestring):
            data = 'j:' + json.dumps(data)
        else:
            data = 'r:' + str(data)

        return self.redis.publish(event_name, data)

    def connect(self, host="127.0.0.1", port=6379):
        log.msg('Event bus connected')
        d = defer.Deferred()
        reactor.connectTCP(host, port, EventBusFactory(d, self))
        return d

    def on(self, pattern, callback):
        if not self.protocol:
            raise Exception('Event bus is not connected yet!')
        self.protocol.on(pattern, callback)
        log.msg('Registered %s for channel: %s' % (callback, pattern))


class EventBusProtocol(redis.SubscriberProtocol):
    callbacks = {}

    def on(self, pattern, callback):
        if not pattern in self.callbacks:
            self.callbacks[pattern] = []

            if '*' in pattern:
                self.psubscribe(pattern)
            else:
                self.subscribe(pattern)

        self.callbacks[pattern].append(callback)

    def connectionMade(self):
        self.factory.eb.protocol = self

        if self.factory.on_connect:
            self.factory.on_connect.callback(self)
            self.factory.on_connect = None
            #
            #print "waiting for messages..."
            #print "use the redis client to send messages:"
            #print "$ redis-cli publish zz test"
            #print "$ redis-cli publish foo.bar hello world"
            #self.subscribe("zz")
            #self.psubscribe("foo.*")
            #reactor.callLater(10, self.unsubscribe, "zz")
            #reactor.callLater(15, self.punsubscribe, "foo.*")

            # self.continueTrying = False
            # self.transport.loseConnection()

    def messageReceived(self, pattern, channel, message):
        log.msg("pattern=%s, channel=%s message=%s" % (pattern, channel, message))

        if message.startswith('j:'):
            message = json.loads(message[2:])
        else:
            message = message[2:]

        callbacks = []
        if pattern and pattern in self.callbacks:
            callbacks = self.callbacks[pattern]
        elif channel and channel in self.callbacks:
            callbacks = self.callbacks[channel]

        for clb in callbacks:
            clb(channel, message)

    def connectionLost(self, reason):
        log.msg("Connection lost: %s" % reason)


class EventBusFactory(redis.SubscriberFactory):
    maxDelay = 120
    continueTrying = True

    protocol = EventBusProtocol

    def __init__(self, on_connect, eb):
        redis.SubscriberFactory.__init__(self)
        self.on_connect = on_connect
        self.eb = eb



