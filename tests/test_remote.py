import sys
import inject

import pytest
from twisted.internet import defer

import txredisapi as redis

from mfcloud.remote import Server, Task


@pytest.inlineCallbacks
def test_exchange():
    inject.clear()



    rc = yield redis.Connection(dbid=2)
    yield rc.flushdb()

    d = defer.Deferred()
    d.task_id = None
    d.args = None

    def _task(task_id, *args):
        d.task_id = task_id
        d.args = args

    server = Server()
    server.register_task('foo', _task)
    server.bind()

    task = Task('foo', 'baz')
    yield task.call()

    assert d.args == ['baz']

    assert task.task_id > 0
    assert task.data == []
    assert task.completed == False

    yield server.send_data(task.task_id, 'nami-nami')

    assert task.data == ['nami-nami']
    assert task.completed == False

    yield d.callback('this is respnse')

    assert task.data == ['nami-nami']
    assert task.completed == True
    assert task.response == 'this is respnse'
