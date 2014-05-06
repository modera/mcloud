import json
from flexmock import flexmock
from mfcloud.events import EventBus
from mfcloud.util import inject_services
from txzmq import ZmqPubConnection


def test_bus_is_passing_events_to_zmq():

    zmq = flexmock()

    def configure(binder):
        binder.bind(ZmqPubConnection, zmq)

    with inject_services(configure):

        zmq.should_receive('publish').with_args(json.dumps({'some': 'data'}), 'event-boo').once()

        eb = EventBus()
        eb.fire_event('boo', some='data')

