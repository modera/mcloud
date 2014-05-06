import json
import inject
from txzmq import ZmqPubConnection


class EventBus(object):

    zmq = inject.attr(ZmqPubConnection)

    def fire_event(self, event_name, **kwargs):
        self.zmq.publish(json.dumps(kwargs), 'event-%s' % event_name)
