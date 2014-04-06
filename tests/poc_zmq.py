import time
from twisted.internet import reactor
from txzmq import ZmqEndpoint, ZmqFactory, ZmqPubConnection, ZmqSubConnection

zf2 = ZmqFactory()
e2 = ZmqEndpoint('connect', 'tcp://127.0.0.1:5555')

s2 = ZmqSubConnection(zf2, e2)
s2.subscribe("")

def doPrint(*args):
    print "message received: %r" % (args, )

s2.gotMessage = doPrint



zf = ZmqFactory()
e = ZmqEndpoint('bind', 'tcp://127.0.0.1:5555')

s = ZmqPubConnection(zf, e)

def publish():
    data = str(time.time())
    print "publishing %r" % data
    s.publish(data)

    reactor.callLater(1, publish)

publish()

reactor.run()

