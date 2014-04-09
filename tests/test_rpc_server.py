from flexmock import flexmock
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


@pytest.inlineCallbacks
def test_xmlrpc_get_result():

    s = ApiRpcServer()

    s.redis = flexmock()
    s.redis.should_receive('get').with_args('mfcloud-ticket-123-result').and_return(defer.succeed('{"foo":"bar"}'))

    r = yield s.xmlrpc_get_result(123)

    assert r == {"foo": "bar"}

@pytest.inlineCallbacks
def test_xmlrpc_is_completed():

    s = ApiRpcServer()

    s.redis = flexmock()
    s.redis.should_receive('get').with_args('mfcloud-ticket-123-completed').and_return(defer.succeed(1))

    r = yield s.xmlrpc_is_completed(123)

    assert r is True


@pytest.inlineCallbacks
def test_task_completed():

    s = ApiRpcServer()

    s.zmq = flexmock()
    s.zmq.should_receive('publish').with_args('{"foo": "bar"}', "task-completed-123").once()

    s.redis = yield txredisapi.Connection(dbid=2)
    yield s.redis.flushdb()

    yield s.task_completed({"foo": "bar"}, 123)

    completed = yield s.redis.get('mfcloud-ticket-123-completed')
    assert completed == 1

    result = yield s.redis.get('mfcloud-ticket-123-result')
    assert result == '{"foo": "bar"}'


@pytest.inlineCallbacks
def test_task_failed():

    s = ApiRpcServer()

    s.zmq = flexmock()

    s.zmq.should_receive('publish').with_args('<foo> bar', "task-failed-123").once()

    yield s.task_failed(flexmock(type='foo', getErrorMessage=lambda: 'bar'), 123)


@pytest.inlineCallbacks
def test_xmlrpc_task_start_no_task():

    s = ApiRpcServer()

    flexmock(s)
    s.redis = flexmock()
    s.redis.should_receive('incr').with_args('mfcloud-ticket-id').and_return(defer.succeed(321))

    r = yield s.xmlrpc_task_start('foo', 'bar', baz='123abc')

    assert isinstance(r, xmlrpc.Fault)
    assert r.faultCode == 1



@pytest.inlineCallbacks
def test_xmlrpc_task_start_proper_exec():

    mock_task = flexmock()
    mock_task.should_receive('task').with_args(321, 'bar', baz='123abc').once().and_return(defer.succeed('bah'))


    s = ApiRpcServer()
    s.tasks = {'foo': mock_task.task}

    flexmock(s)

    s.should_receive('task_completed').with_args('bah', 321)

    s.redis = flexmock()
    s.redis.should_receive('incr').with_args('mfcloud-ticket-id').and_return(defer.succeed(321))

    r = yield s.xmlrpc_task_start('foo', 'bar', baz='123abc')

    assert r == {'ticket_id': 321}


@pytest.inlineCallbacks
def test_xmlrpc_task_start_exec_fail():

    mock_task = flexmock()
    mock_task.should_receive('task').with_args(321, 'bar', baz='123abc').once().and_return(defer.fail(Exception('Foo')))


    s = ApiRpcServer()
    s.tasks = {'foo': mock_task.task}

    flexmock(s)

    s.should_receive('task_failed').with_args(xmlrpc.Fault, 321)

    s.redis = flexmock()
    s.redis.should_receive('incr').with_args('mfcloud-ticket-id').and_return(defer.succeed(321))

    r = yield s.xmlrpc_task_start('foo', 'bar', baz='123abc')

    assert r == {'ticket_id': 321}




