import sys
from flexmock import flexmock
import inject
from mfcloud.events import EventBus
from mfcloud.rpc_server import ApiRpcServer
from mfcloud.txdocker import IDockerClient, DockerTwistedClient
from mfcloud.util import txtimeout

import pytest

from mfcloud.remote import Server, Client, ApiError, Task
from twisted.internet import reactor, defer
from twisted.python import log

import txredisapi as redis


class MockServer(Server):
    message = None

    def on_message(self, client, message, isBinary=False):
        self.message = message


class MockClient(Client):
    message = None

    def on_message(self, message, isBinary=False):
        self.message = message


def sleep(secs):
    d = defer.Deferred()
    reactor.callLater(secs, d.callback, None)
    return d


#@pytest.inlineCallbacks
#def test_exchange():
#    inject.clear()
#
#    #log.startLogging(sys.stdout)
#
#    server = MockServer(port=9999)
#    server.bind()
#
#    assert len(server.clients) == 0
#
#    client = MockClient(port=9999)
#    yield client.connect()
#
#    assert len(server.clients) == 1
#
#    log.msg('Sending data')
#    yield client.send('boo')
#
#    yield sleep(0.1)
#
#    assert server.message == 'boo'
#
#    yield server.clients[0].sendMessage('baz')
#
#    yield sleep(0.1)
#
#    assert client.message == 'baz'
#
#    client.shutdown()
#    server.shutdown()
#
#    yield sleep(0.1)

@pytest.inlineCallbacks
def test_request_response():
    inject.clear()

    server = Server(port=9998)
    server.bind()

    client = Client(port=9998)
    yield client.connect()

    response = yield client.call_sync('ping')

    assert response == 'pong'


@pytest.inlineCallbacks
def test_request_response_no_such_command():
    inject.clear()

    log.startLogging(sys.stdout)

    server = Server(port=9996)
    server.bind()

    client = Client(port=9996)
    yield client.connect()

    with pytest.raises(ApiError):
        yield client.call_sync('hoho')


@pytest.inlineCallbacks
def test_tasks():
    #inject.clear()
    #
    #log.startLogging(sys.stdout)
    #
    #rc = yield redis.Connection(dbid=2)
    #yield rc.flushdb()
    #
    task_defered = defer.Deferred()

    task = flexmock()
    task.should_receive('foo').with_args(int, 123, 'test').once().and_return(task_defered)
    #
    #server = Server(port=9997)
    #server.register_task(task, 'foo')
    #server.bind()
    #
    #client = MockClient(port=9997)
    #yield client.connect()
    #
    #task = yield client.call_sync('task_start', 'baz')

    inject.clear()

    rc = yield redis.Connection(dbid=2)
    eb = EventBus(redis)
    yield eb.connect()

    api = ApiRpcServer()
    api.tasks['baz'] = task.foo

    def my_config(binder):
        binder.bind(redis.Connection, rc)
        binder.bind(EventBus, eb)
        binder.bind(ApiRpcServer, api)

    inject.configure(my_config)

    yield rc.flushdb()

    server = Server(port=9997)
    server.bind()

    client = Client(port=9997)
    yield client.connect()

    task = Task('baz')

    yield client.call(task, 123, 'test')

    yield sleep(0.1)

    assert task.id > 0
    assert task.name == 'baz'

    assert task.is_running
    #
    yield sleep(0.1)

    #    ps = yield client.ps()
    #    assert len(ps) == 1
    #    assert ps[task.id] == task.name
    #
    #
    assert task.data == []
    assert task.response is None

    yield server.send_task_progress(task.id, 'nami-nami')

    yield sleep(0.1)

    assert task.data == ['nami-nami']
    assert task.is_running == False
    assert task.response is None

    #    ##yield d.callback('this is respnse')
    #    #
    #    #yield sleep(0.1)
    #    #
    #    #assert task.data == ['nami-nami']
    #    #assert task.completed == True
    #    #assert task.response == 'this is respnse'
    #    #
    #    #client.shutdown()
    #    #server.shutdown()
    #    #
    #    #yield sleep(0.1)