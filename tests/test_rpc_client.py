from mcloud.rpc_client import ApiRpcClient
import pytest


@pytest.fixture
def client():
    return ApiRpcClient()


def test_ref_expression_app(client):
    result = client.parse_app_ref('foo.boo', {})

    assert result == ('boo', None)


def test_ref_expression_app(client):
    result = client.parse_app_ref('foo.boo', {})

    assert result == ('boo', 'foo')

def test_ref_app_in_args(client):
    result = client.parse_app_ref('boo.', {'app': 'foo'})

    assert result == ('foo', 'boo')


# def test_ref_empty(client):
#     result = client.parse_app_ref('', {})
#
#     assert result == ('mcloud', None)   # mcloud is current dir

def test_ref_require_app(client):

    with pytest.raises(ValueError):
        client.parse_app_ref('a.b.c.d.e.f', {}, require_app=True)

def test_ref_app_only_with_service(client):

    with pytest.raises(ValueError):
        client.parse_app_ref('foo.boo', {}, app_only=True)

def test_ref_requeire_service_without_service(client):

    with pytest.raises(ValueError):
        client.parse_app_ref('boo', {}, require_service=True)


def test_ref_need_host(client):

    client.host = 'my.host'
    result = client.parse_app_ref('foo.boo', {}, require_host=True)

    assert result == ('my.host', 'boo', 'foo')


def test_ref_need_host_specified_hostname(client):

    client.host = 'my.host'
    result = client.parse_app_ref('foo.boo@some-host.at.some.location.ua', {}, require_host=True)

    assert result == ('some-host.at.some.location.ua', 'boo', 'foo')



def test_ref_need_host_specified_ip(client):

    client.host = 'my.host'
    result = client.parse_app_ref('foo.boo@192.168.0.32', {}, require_host=True)

    assert result == ('192.168.0.32', 'boo', 'foo')


def test_with_on_host(client):

    client.host = 'foo'

    assert client.host == 'foo'

    with client.override_host('boo'):
        assert client.host == 'boo'

    assert client.host == 'foo'