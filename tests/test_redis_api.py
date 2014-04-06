import pytest


import txredisapi as redis

@pytest.inlineCallbacks
def test_incr():
    rc = yield redis.Connection(dbid=2)
    yield rc.flushdb()

    yield rc.set("foo", 4)

    v = yield rc.get("foo")

    assert v == 4

    v = yield rc.incr("foo")

    assert v == 5

    yield rc.disconnect()

@pytest.inlineCallbacks
def test_hash_set():

    rc = yield redis.Connection(dbid=2)
    yield rc.flushdb()

    yield rc.hset("foo", "bar", "baz")

    v = yield rc.hget("foo", "bar")

    assert v == 'baz'