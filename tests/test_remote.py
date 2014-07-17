import sys
import inject

import pytest

from mfcloud.remote import Server, Client
from twisted.internet import reactor, defer
from twisted.python import log

import txredisapi as redis
from mfcloud.remote import Server, Task


class MockServer(Server):

    message = None

    def on_message(self, message, isBinary=False):
        self.message = message


class MockClient(Client):
    message = None

    def on_message(self, message, isBinary=False):
        self.message = message


def sleep(secs):
    d = defer.Deferred()
    reactor.callLater(secs, d.callback, None)
    return d


@pytest.inlineCallbacks
def test_exchange():
    inject.clear()

    #log.startLogging(sys.stdout)

    server = MockServer(port=9999)
    server.bind()

    assert len(server.clients) == 0

    client = MockClient(port=9999)
    yield client.connect()

    assert len(server.clients) == 1

    log.msg('Sending data')
    yield client.send('boo')

    yield sleep(0.1)

    assert server.message == 'boo'

    yield server.clients[0].sendMessage('baz')

    yield sleep(0.1)

    assert client.message == 'baz'

    client.shutdown()
    server.shutdown()

    yield sleep(0.1)



@pytest.inlineCallbacks
def test_tasks():
    inject.clear()

    rc = yield redis.Connection(dbid=2)
    yield rc.flushdb()

    d = defer.Deferred()
    d.task_id = None
    d.args = None

    def _task(task_id, *args):
        d.task_id = task_id
        d.args = args

    server = Server(port=9998)
    server.register_task('foo', _task)
    server.bind()


    client = Client(port=9998)

    task = Task('foo', 'baz')

    yield client.call(task)

    yield sleep(0.1)

    assert d.args == ['baz']

    assert task.task_id > 0
    assert task.data == []
    assert task.completed == False

    yield server.send_data(task.task_id, 'nami-nami')

    yield sleep(0.1)

    assert task.data == ['nami-nami']
    assert task.completed == False

    yield d.callback('this is respnse')

    yield sleep(0.1)

    assert task.data == ['nami-nami']
    assert task.completed == True
    assert task.response == 'this is respnse'

    client.shutdown()
    server.shutdown()

    yield sleep(0.1)