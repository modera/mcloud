import sys
from mfcloud.events import EventBus
from mfcloud.txdocker import IDockerClient, DockerTwistedClient
from mfcloud.util import injector
import os
from flexmock import flexmock
from mfcloud.config import YamlConfig
from mfcloud.container import DockerfileImageBuilder
from mfcloud.service import Service
from mfcloud.test_utils import real_docker
import pytest
from twisted.internet import defer
import txredisapi


def test_service_init():

    builder = flexmock(read=lambda: 'boo')
    s = Service(
        image_builder=builder,
        name='foo',
        volumes=[{'foo': 'bar'}],
        command='some --cmd',
        env={'baz': 'bar'}
    )

    assert s.image_builder == builder
    assert s.name == 'foo'
    assert s.volumes == [{'foo': 'bar'}]
    assert s.command == 'some --cmd'
    assert s.env == {'baz': 'bar'}


def test_inspected():

    s = Service()
    s._inspected = True

    assert s.is_inspected() is True


def test_not_inspected():

    s = Service()
    assert s.is_inspected() is False


@pytest.inlineCallbacks
def test_inspect():

    s = Service(name='foo', client=flexmock())

    s.client.should_receive('inspect').with_args('foo').ordered().and_return(defer.succeed({'foo': 'bar'}))

    assert s.is_inspected() is False

    r = yield s.inspect()
    assert r == {'foo': 'bar'}

    assert s.is_inspected() is True

    assert s._inspect_data == {'foo': 'bar'}


@pytest.mark.parametrize("method", [
    'is_created',
    'is_running',
])
def test_no_lazy_inspect_not_inspected(method):

    s = Service(name='foo', client=flexmock())
    s._inspected = False

    with pytest.raises(Service.NotInspectedYet):
        getattr(s, method)()


@pytest.mark.parametrize("method", [
    'is_created',
    'is_running',
])
def test_no_lazy_inspect(method):

    s = Service(name='foo', client=flexmock())
    s._inspected = True
    s._inspect_data = {'State': {'Running': True}}

    getattr(s, method)()


def test_wrong_inspect_data():

    s = Service()
    s._inspected = True
    s._inspect_data = {'foo': 'bar'}

    assert not s.is_running()


def test_is_inspected():

    s = Service()

    assert not s.is_inspected()


@pytest.inlineCallbacks
def test_create():

    s = Service()
    s.name = 'my_service'
    flexmock(s)

    s.image_builder = flexmock()
    s.image_builder.should_receive('build_image').with_args(ticket_id=123123).ordered().once().and_return(defer.succeed('boo'))

    s.client = flexmock()
    s.client.should_receive('create_container').with_args({
        "Hostname": 'my_service',
        "Image": 'boo'
    }, 'my_service', ticket_id=123123).ordered().once().and_return('magic')

    s.should_receive('inspect').with_args().ordered().once().and_return('magic')

    r = yield s.create(ticket_id=123123)

    assert r == 'magic'



@pytest.inlineCallbacks
@pytest.mark.xfail
def test_start():

    with injector({'dns-server': 'local.dns', 'dns-search-suffix': 'local'}):

        s = Service()
        s.name = 'my_service'
        flexmock(s)

        s.client = flexmock()

        s.client.should_receive('find_container_by_name').with_args('my_service').once().and_return(defer.succeed('123abc'))
        s.client.should_receive('start_container').with_args('123abc', ticket_id=123123, config={'DnsSearch': 'None.local', 'Dns': ['local.dns']}).once().and_return(defer.succeed('boo'))
        s.should_receive('inspect').with_args().once().and_return(defer.succeed('baz'))

        r = yield s.start(ticket_id=123123)

        assert r == 'baz'


@pytest.inlineCallbacks
@pytest.mark.xfail
def test_start_volumes():

    with injector({'dns-server': 'local.dns', 'dns-search-suffix': 'local'}):
        s = Service()
        s.name = 'my_service'
        s.volumes = [
            {'local': '/base/path/foo1', 'remote': '/bar1'},
            {'local': '/base/path/foo2', 'remote': '/bar2'},
            {'local': '/base/path/foo3', 'remote': '/bar3'}
        ]
        flexmock(s)

        s.client = flexmock()

        s.client.should_receive('find_container_by_name').with_args('my_service').once().and_return(defer.succeed('123abc'))
        s.client.should_receive('start_container').with_args('123abc', ticket_id=123123, config={
            "Binds": ['/base/path/foo1:/bar1', '/base/path/foo2:/bar2', '/base/path/foo3:/bar3'],
            'DnsSearch': 'None.local',
            'Dns': ['local.dns']
        }).once().and_return(defer.succeed('boo'))
        s.should_receive('inspect').with_args().once().and_return(defer.succeed('baz'))

        r = yield s.start(ticket_id=123123)

        assert r == 'baz'

@pytest.inlineCallbacks
@pytest.mark.xfail
def test_start_volumes_from():

    with injector({'dns-server': 'local.dns', 'dns-search-suffix': 'local'}):
        s = Service()
        s.name = 'my_service'
        s.volumes_from = ['foo', 'bar']

        flexmock(s)

        s.client = flexmock()

        s.client.should_receive('find_container_by_name').with_args('my_service').once().and_return(defer.succeed('123abc'))
        s.client.should_receive('start_container').with_args('123abc', ticket_id=123123, config={
            "VolumesFrom": ['foo', 'bar'],
            'DnsSearch': 'None.local',
            'Dns': ['local.dns']
        }).once().and_return(defer.succeed('boo'))
        s.should_receive('inspect').with_args().once().and_return(defer.succeed('baz'))

        r = yield s.start(ticket_id=123123)

        assert r == 'baz'

@pytest.inlineCallbacks
@pytest.mark.xfail
def test_start_ports():

    with injector({'dns-server': 'local.dns', 'dns-search-suffix': 'local'}):
        s = Service()
        s.name = 'my_service'
        s.ports = ['22/tcp']

        flexmock(s)

        s.client = flexmock()

        s.client.should_receive('find_container_by_name').with_args('my_service').once().and_return(defer.succeed('123abc'))
        s.client.should_receive('start_container').with_args('123abc', ticket_id=123123, config={
            "PortBindings": {'22/tcp': [{}]},
            'DnsSearch': 'None.local',
            'Dns': ['local.dns']
        }).once().and_return(defer.succeed('boo'))
        s.should_receive('inspect').with_args().once().and_return(defer.succeed('baz'))

        r = yield s.start(ticket_id=123123)

        assert r == 'baz'


def test_generate_config():

    s = Service()
    s.name = 'my_service'

    assert s._generate_config('foo') == {
        "Hostname": 'my_service',
        "Image": 'foo'
    }

def test_generate_config_volumes():

    s = Service()
    s.name = 'my_service'
    s.volumes = [
        {'local': '/base/path/foo1', 'remote': '/bar1'},
        {'local': '/base/path/foo2', 'remote': '/bar2'},
        {'local': '/base/path/foo3', 'remote': '/bar3'}
    ]

    assert s._generate_config('foo') == {
        "Hostname": 'my_service',
        "Image": 'foo',
        "Volumes": {
            "/bar1": {},
            "/bar2": {},
            "/bar3": {},
        }
    }

def test_generate_config_env():

    s = Service()
    s.name = 'my_service'
    s.env = {'FOO': 'bar', 'BAZ': 'foo'}

    assert s._generate_config('foo') == {
        "Hostname": 'my_service',
        "Image": 'foo',
        "Env": ['FOO=bar', 'BAZ=foo']
    }


@pytest.inlineCallbacks
def test_service_api():
    from twisted.python import log
    log.startLogging(sys.stdout)

    redis = yield txredisapi.Connection(dbid=2)
    yield redis.flushdb()

    yield redis.set('mfcloud-ticket-id', 123122)

    eb = EventBus(redis)
    yield eb.connect()

    with injector({EventBus: eb, 'dns-server': 'local.dns', 'dns-search-suffix': 'local', IDockerClient: DockerTwistedClient()}):

        name = 'test.foo'

        s = Service(
            image_builder=DockerfileImageBuilder(os.path.join(os.path.dirname(__file__), '_files/ct_bash')),
            name=name
        )

        class Printer(object):
            def publish(self, *args):
                print args

        s.client.message_publisher = Printer()

        yield s.inspect()

        assert not s.is_created()
        assert not s.is_running()

        yield s.create(ticket_id=123123)
        assert s.is_created()
        assert not s.is_running()

        yield s.start(ticket_id=123123)
        assert s.is_created()
        assert s.is_running()


        yield s.stop(ticket_id=123123)
        assert s.is_created()
        assert not s.is_running()

        yield s.destroy(ticket_id=123123)
        assert not s.is_created()
        assert not s.is_running()