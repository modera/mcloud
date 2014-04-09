import argparse
from flexmock import flexmock
from mfcloud.rpc_client import ApiRpcClient, populate_client_parser
import pytest
from twisted.application.reactors import Reactor
from twisted.internet import reactor, defer
from twisted.web.xmlrpc import Proxy


@pytest.fixture
def client():
    return ApiRpcClient()


def test_init(client):
    flexmock(client)
    client.should_receive('init_zmq').once()

    ApiRpcClient.__init__(client)

    assert isinstance(client.proxy, Proxy)
    assert client.reactor is reactor


def test_task_failed(client):
    flexmock(client)
    client.reactor = flexmock()

    client.reactor.should_receive('stop').once()

    client._task_failed('boo')


def test_task_completed_json(client):
    flexmock(client)
    client.reactor = flexmock()

    client.reactor.should_receive('stop').once()
    client.should_receive('on_result').with_args({"foo": "bar"}).once()

    client._task_completed('{"foo": "bar"}')


@pytest.inlineCallbacks
def test_remote_exec(client):
    flexmock(client)
    client.reactor = flexmock()
    client.proxy = flexmock()

    client.proxy.should_receive('callRemote').with_args('task_start', 'foo', 'hoho', 'hehe') \
        .and_return(defer.succeed({'ticket_id': 123})).ordered().once()

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

    client.proxy.should_receive('callRemote').with_args('task_start', 'foo', 'hoho', 'hehe') \
        .and_return(defer.fail(Exception)).ordered().once()

    # on some strange reason order should be defined like this
    client.reactor.should_receive('stop').once().ordered()
    client.reactor.should_receive('run').once().ordered()

    on_result = lambda: 'boo'

    yield client._remote_exec('foo', on_result, 'hoho', 'hehe')

    assert client.on_result is on_result
    assert client.ticket == {}


def test_populeate_is_syntactically_correct():
    arg_parser = argparse.ArgumentParser()
    subparsers = arg_parser.add_subparsers()
    populate_client_parser(subparsers)


def test_on_message_task_completed(client):
    flexmock(client)

    client.ticket = {'ticket_id': 123}

    client.should_receive('_task_completed').with_args('foo')

    client._on_message('foo', 'task-completed-123')


def test_on_message_task_failed(client):
    flexmock(client)

    client.ticket = {'ticket_id': 123}

    client.should_receive('_task_failed').with_args('foo')

    client._on_message('foo', 'task-failed-123')


def test_on_message_message(client, capsys):
    flexmock(client)

    client.ticket = {'ticket_id': 123}
    client._on_message('"foo"', 'log-123')
    out, err = capsys.readouterr()
    assert out == 'foo\n'



