import json
from flexmock import flexmock
import inject
from mfcloud.events import EventBus
from mfcloud.util import inject_services
import pytest
from twisted.internet import reactor
from txzmq import ZmqPubConnection



import txredisapi as redis

@pytest.inlineCallbacks
def test_events():
    inject.clear()
    rc = yield redis.Connection(dbid=2)
    yield rc.flushdb()

    eb = EventBus(rc)
    yield eb.connect()

    test_events.test = None

    def boo(pattern, message):
        assert message == 'hoho'
        assert pattern == 'foo'
        test_events.test = message

    eb.on('foo', boo)

    yield eb.fire_event('foo', 'hoho')

    def check_results():
        assert test_events.test == 'hoho'

    reactor.callLater(50, check_results)


@pytest.inlineCallbacks
def test_events_pattern():
    inject.clear()
    rc = yield redis.Connection(dbid=2)
    yield rc.flushdb()

    eb = EventBus(rc)
    yield eb.connect()

    test_events_pattern.test = None

    def boo(pattern, message):
        assert message == 'hoho'
        assert pattern == 'foo.baz'
        test_events_pattern.test = message

    eb.on('foo.*', boo)

    yield eb.fire_event('foo.baz', 'hoho')

    def check_results():
        assert test_events_pattern.test == 'hoho'

    reactor.callLater(50, check_results)


@pytest.inlineCallbacks
def test_events_pattern_wrong():
    inject.clear()
    rc = yield redis.Connection(dbid=2)
    yield rc.flushdb()

    eb = EventBus(rc)
    yield eb.connect()

    test_events_pattern_wrong.test = None

    def boo(pattern, message):
        assert message == 'hoho'
        assert pattern == 'foo.baz'
        test_events_pattern_wrong.test = message

    eb.on('bar.*', boo)

    yield eb.fire_event('foo.baz', 'hoho')

    def check_results():
        assert test_events_pattern_wrong.test is None

    reactor.callLater(50, check_results)


#
#
#def test_bus_is_passing_events_to_zmq():
#
#    zmq = flexmock()
#
#    def configure(binder):
#        binder.bind(ZmqPubConnection, zmq)
#
#    with inject_services(configure):
#
#        zmq.should_receive('publish').with_args(json.dumps({'some': 'data'}), 'event-boo').once()
#
#        eb = EventBus()
#        eb.fire_event('boo', some='data')

