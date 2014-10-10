import sys
from flexmock import flexmock
import inject
from mcloud.events import EventBus
from mcloud.txdocker import IDockerClient, DockerTwistedClient
from mcloud.util import txtimeout

import pytest

from mcloud.remote import Server, Client, ApiError, Task, ApiRpcServer
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
    #-----------------------------------
    # preparations
    #-----------------------------------

    # cleanup a bit
    inject.clear()

    def my_config(binder):
        binder.bind('settings', None)
    inject.configure(my_config)


    #log.startLogging(sys.stdout)

    server = Server(port=9998)
    server.bind()

    client = Client(port=9998)
    yield client.connect()

    response = yield client.call_sync('ping')

    assert response == 'pong'

    client.shutdown()
    server.shutdown()


@pytest.inlineCallbacks
def test_request_response_no_such_command():
    #-----------------------------------
    # preparations
    #-----------------------------------

    # cleanup a bit
    inject.clear()

    def my_config(binder):
        binder.bind('settings', None)
    inject.configure(my_config)


    log.startLogging(sys.stdout)

    server = Server(port=9996)
    server.bind()

    client = Client(port=9996)
    yield client.connect()

    with pytest.raises(ApiError):
        yield client.call_sync('hoho')

    client.shutdown()
    server.shutdown()


@pytest.inlineCallbacks
def test_tasks():

    #-----------------------------------
    # preparations
    #-----------------------------------

    # cleanup a bit
    inject.clear()

    rc = yield redis.Connection(dbid=2)
    eb = EventBus(rc)
    yield eb.connect()

    def my_config(binder):
        binder.bind(redis.Connection, rc)
        binder.bind(EventBus, eb)
        binder.bind('settings', None)

    inject.configure(my_config)

    yield rc.flushdb()

    api = inject.instance(ApiRpcServer)


    #-----------------------------------
    # Test itself
    #-----------------------------------

    # this will emulate some long-running process
    task_defered = defer.Deferred()


    # this is mock that will execute our long-running process
    task = flexmock()
    task.should_receive('foo').with_args(int, 123, 'test').once().and_return(task_defered)

    # register our task
    api.tasks['baz'] = task.foo

    # start server -> real server on tcp port
    server = Server(port=9997)
    server.bind()

    # real client connecton here
    client = Client(port=9997)
    yield client.connect()


    # client calls a task
    task = Task('baz')
    yield client.call(task, 123, 'test')

    yield sleep(0.1)

    assert task.id > 0
    assert task.name == 'baz'

    assert task.is_running is True

    assert len(server.rpc_server.tasks_running) == 1
    assert server.rpc_server.tasks_running[task.id]['name'] == 'baz'
    assert len(server.rpc_server.task_list()) == 1

    # no data should be on client
    yield sleep(0.1)
    assert task.data == []
    assert task.response is None

    # now server sends some progress
    yield server.clients[0].send_event('task.progress.%s' % task.id, 'nami-nami')


    # and client should receive this data
    yield sleep(0.1)

    assert task.data == ['nami-nami']
    assert task.is_running is True
    assert task.response is None

    # now our long-running process stopped and returned some result
    yield task_defered.callback('this is respnse')


    # and client should recieve this resul
    yield sleep(0.1)

    assert task.data == ['nami-nami']
    assert task.is_running == False
    assert task.response == 'this is respnse'

    assert len(server.rpc_server.tasks_running) == 0
    assert len(server.rpc_server.task_list()) == 0


    #-----------------------------------
    # Cleanup
    #-----------------------------------

    client.shutdown()
    server.shutdown()

    yield sleep(0.1)


@pytest.inlineCallbacks
def test_task_terminate():

    #-----------------------------------
    # preparations
    #-----------------------------------

    # cleanup a bit
    inject.clear()

    rc = yield redis.Connection(dbid=2)
    eb = EventBus(rc)
    yield eb.connect()

    def my_config(binder):
        binder.bind(redis.Connection, rc)
        binder.bind(EventBus, eb)
        binder.bind('settings', None)

    inject.configure(my_config)

    yield rc.flushdb()

    api = inject.instance(ApiRpcServer)


    #-----------------------------------
    # Test itself
    #-----------------------------------

    # this will emulate some long-running process
    task_defered = defer.Deferred()


    # this is mock that will execute our long-running process
    task = flexmock()
    task.should_receive('foo').with_args(int, 123, 'test').once().and_return(task_defered)

    # register our task
    api.tasks['baz'] = task.foo

    # start server -> real server on tcp port
    server = Server(port=9997)
    server.bind()

    # real client connecton here
    client = Client(port=9997)
    yield client.connect()


    # client calls a task
    task = Task('baz')
    yield client.call(task, 123, 'test')

    yield sleep(0.1)

    assert task.id > 0
    assert task.name == 'baz'

    assert task.is_running is True


    # now client terminates the task
    yield sleep(0.1)

    client.terminate_task(task.id)

    yield sleep(0.1)

    assert task.is_running is False

    #-----------------------------------
    # Cleanup
    #-----------------------------------

    client.shutdown()
    server.shutdown()

    yield sleep(0.1)