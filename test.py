from mcloud.django.startup import init_django
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall
from twisted.web import server, resource
from twisted.internet import reactor, endpoints, defer

init_django()

from mcloud.app.models import Deployment

@inlineCallbacks
def hyper_task():
    boo = yield Deployment.tx.all()
    print(boo)


lc = LoopingCall(hyper_task)
lc.start(1)

reactor.run()