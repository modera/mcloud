from flexmock import flexmock
from mfcloud.rpc_client import ApiRpcClient
import pytest
from twisted.application.reactors import Reactor
from twisted.internet import reactor
from twisted.web.xmlrpc import Proxy


@pytest.fixture
def client():
    client = ApiRpcClient()

    return client


def test_init(client):

    flexmock(client)

    client.should_receive('init_zmq')

    assert isinstance(client.proxy, Proxy)
    assert client.reactor is reactor



