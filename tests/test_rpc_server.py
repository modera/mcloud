from flexmock import flexmock
from mfcloud.events import EventBus
from mfcloud.rpc_server import ApiRpcServer
from mfcloud.util import inject_services
import pytest
from twisted.internet import defer, reactor
from twisted.web import xmlrpc
import txredisapi


@pytest.inlineCallbacks
def test_ticket_created():

    redis = yield txredisapi.Connection(dbid=2)
    yield redis.flushdb()

    yield redis.set('mfcloud-ticket-id', 123122)

    eb = EventBus(redis)
    yield eb.connect()

    def configure(binder):
        binder.bind(txredisapi.Connection, redis)
        binder.bind(EventBus, eb)

    with inject_services(configure):

        task_defered = defer.Deferred()

        def task(ticket_id, arg):
            assert ticket_id == 123123
            assert arg == 'baz'

            return task_defered

        server = ApiRpcServer()
        server.tasks['foo'] = task

        client = flexmock()
        result = yield server.task_start(client, 'foo', 'baz')

        assert result == '{"id": 123123, "success": true}'

