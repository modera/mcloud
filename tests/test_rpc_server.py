from flexmock import flexmock
from mfcloud.rpc_server import ApiRpcServer
from mfcloud.util import inject_services
import pytest
from twisted.internet import defer, reactor
import txredisapi


@pytest.inlineCallbacks
def test_ticket_created():

    redis = yield txredisapi.Connection(dbid=2)
    yield redis.flushdb()

    yield redis.set('mfcloud-ticket-id', 123122)

    def configure(binder):
        binder.bind(txredisapi.Connection, redis)

    with inject_services(configure):


        task_defered = defer.Deferred()

        def task(ticket_id, arg):
            assert ticket_id == 123123
            assert arg == 'baz'

            return task_defered

        server = ApiRpcServer()
        server.tasks['foo'] = task

        result = yield server.xmlrpc_task_start('foo', 'baz')

        assert result['ticket_id'] == 123123

        result = yield server.xmlrpc_is_completed(123123)
        assert result is False

        yield task_defered.callback({'foo': 'bar'})

        result = yield server.xmlrpc_is_completed(123123)
        assert result is True

        result = yield server.xmlrpc_get_result(123123)
        assert result == {'foo': 'bar'}



