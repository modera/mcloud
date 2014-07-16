import sys
import inject

import pytest

from mfcloud.remote import Server, Client
from twisted.python import log


class MockServer(Server):

    message = None

    def on_message(self, message):
        self.message = message


class MockClient(Client):
    message = None

    def on_message(self, message):
        self.message = message


@pytest.inlineCallbacks
def test_exchange():
    inject.clear()
    log.startLogging(sys.stdout)
    log.msg('Hello, world.')

    server = MockServer(port=9999)
    server.bind()

    assert len(server.clients) == 0

    client = MockClient(port=9999)
    yield client.connect()

    assert len(server.clients) == 1

    yield client.send('boo')

    #assert server.message == 'boo'

    yield server.clients[0].send('baz')

    assert client.message == 'baz'
