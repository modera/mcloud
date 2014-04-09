from flexmock import flexmock
from mfcloud.rpc_client import ApiRpcClient
import pytest
from twisted.application.reactors import Reactor
from twisted.internet import reactor, defer
from twisted.web.xmlrpc import Proxy


@pytest.fixture
def client():
    return ApiRpcClient()


def test_init(client):

    flexmock(client)

    client.should_receive('init_zmq')

    assert isinstance(client.proxy, Proxy)
    assert client.reactor is reactor


def test_task_failed(client):
    flexmock(client)
    client.reactor = flexmock()

    client.reactor.should_receive('stop')

def test_task_completed_json(client):
    flexmock(client)
    client.reactor = flexmock()

    client.reactor.should_receive('stop')
    client.should_receive('on_result').with_args({"foo": "bar"})

    client._task_completed('{"foo": "bar"}')


@pytest.inlineCallbacks
def test_remote_exec(client):

    flexmock(client)
    client.reactor = flexmock()
    client.proxy = flexmock()

    client.proxy.should_receive('callRemote').with_args('task_start', 'foo', 'hoho', 'hehe')\
        .and_return(defer.succeed({'ticket_id': 123})).ordered()

    client.reactor.should_receive('stop').never()
    client.reactor.should_receive('run').once().ordered()

    on_result = lambda: 'boo'

    yield client._remote_exec('foo', on_result, 'hoho', 'hehe')

    assert client.on_result is on_result
    assert client.ticket['ticket_id'] == 123


@pytest.inlineCallbacks
def test_remote_exec_fail(client):

    flexmock(client)
    client.reactor = flexmock()
    client.proxy = flexmock()

    client.proxy.should_receive('callRemote').with_args('task_start', 'foo', 'hoho', 'hehe')\
        .and_return(defer.fail(Exception)).ordered()

    # on some strange reason order should be defined like this
    client.reactor.should_receive('stop').once().ordered()
    client.reactor.should_receive('run').once().ordered()

    on_result = lambda: 'boo'

    yield client._remote_exec('foo', on_result, 'hoho', 'hehe')

    assert client.on_result is on_result
    assert client.ticket == {}







