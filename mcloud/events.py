import json

from twisted.internet import reactor, defer
import txredisapi as redis
from twisted.python import log
from mcloud.util import txtimeout


class EventBus(object):
    redis = None
    protocol = None

    def __init__(self, redis_connection):
        super(EventBus, self).__init__()
        self.redis = redis_connection

    def fire_event(self, event_name, data=None,  *args, **kwargs):
        if not data:
            if kwargs:
                data = kwargs
            elif args:
                data = args

        if not isinstance(data, basestring):
            data = 'j:' + json.dumps(data)
        else:
            data = 'b:' + str(data)

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

    def cancel(self, pattern, callback):
        if not self.protocol:
            raise Exception('Event bus is not connected yet!')
        self.protocol.cancel(pattern, callback)
        log.msg('unRegistered %s for channel: %s' % (callback, pattern))

    def once(self, pattern, callback):
        if not self.protocol:
            raise Exception('Event bus is not connected yet!')

        def _once_and_remove(*args, **kwargs):
            self.protocol.cancel(pattern, _once_and_remove)
            callback(*args, **kwargs)

        self.protocol.on(pattern, _once_and_remove)
        log.msg('Registered %s for single invocation on channel: %s' % (callback, pattern))

    def wait_for_event(self, pattern, timeout=False):
        d = defer.Deferred()

        def _on_message(channel, message):
            if not d.called:
                d.callback(message)

        self.on(pattern, _on_message)

        if not timeout == 0:
            return txtimeout(d, timeout, lambda: d.callback(None))
        else:
            return d


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

    def cancel(self, pattern, callback):
        if pattern in self.callbacks:
            self.callbacks[pattern].remove(callback)

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



