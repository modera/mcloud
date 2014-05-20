from flexmock import flexmock
from mfcloud.application import ApplicationController, Application
from mfcloud.deployment import Deployment, DeploymentController, DeploymentDoesNotExist
from mfcloud.events import EventBus
from mfcloud.txdocker import IDockerClient
from mfcloud.util import inject_services
import pytest
from twisted.internet import defer
import txredisapi
from txzmq import ZmqPubConnection


def test_deployment_new_instance():

    d = Deployment(public_domain='foo.bar', name='baz', apps=['v1.baz', 'v2.baz'], public_app='myapp',)

    assert d.name == 'baz'
    assert d.public_domain == 'foo.bar'
    assert d.public_app == 'myapp'

    assert len(d.apps) == 2
    assert d.apps == ['v1.baz', 'v2.baz']

    assert d.config == {
        'name': 'baz',
        'public_app': 'myapp',
        'public_domain': 'foo.bar',
        'apps': ['v1.baz', 'v2.baz'],
    }



@pytest.inlineCallbacks
def test_load_data():

    ac = flexmock()
    docker = flexmock()

    docker.should_receive('find_container_by_name').and_return(defer.succeed(None))

    def configure(binder):
        binder.bind(ApplicationController, ac)
        binder.bind(IDockerClient, docker)

    with inject_services(configure):

        ac.should_receive('get').with_args('v1.baz').and_return(defer.succeed(Application({'source': 'srv: {image: bar}'}, 'v1.baz'))).once()
        ac.should_receive('get').with_args('v2.baz').and_return(defer.succeed(Application({'source': 'srv: {image: baz}'}, 'v2.baz'))).once()


        d = Deployment(public_domain='foo.bar', name='baz', apps=['v1.baz', 'v2.baz'])
        config = yield d.load_data(skip_validation=True)

        assert config == {
            'name': 'baz',
            'public_domain': 'foo.bar',
            'public_app': None,
            'apps': [
                {
                    'name': 'v1.baz',
                    'config': {
                        'source': 'srv: {image: bar}'
                    },
                    'services':[{
                        'ip': None,
                        'name': 'srv.v1.baz',
                        'running': False
                    }]
                },
                {
                    'name': 'v2.baz',
                    'config': {
                        'source': 'srv: {image: baz}'
                    },
                    'services': [{
                            'ip': None,
                            'name': 'srv.v2.baz',
                            'running': False
                    }]
                }
            ]
        }


@pytest.inlineCallbacks
def test_deployment_controller():

    redis = yield txredisapi.Connection(dbid=2)
    yield redis.flushdb()

    eb = flexmock()

    def configure(binder):
        binder.bind(txredisapi.Connection, redis)
        binder.bind(EventBus, eb)

    with inject_services(configure):
        controller = DeploymentController()

        with pytest.raises(DeploymentDoesNotExist):
            yield controller.get('foo')

        eb.should_receive('fire_event').with_args('new-deployment', public_app=None, apps=[], name='foo', public_domain='foo.bar').once()
        eb.should_receive('fire_event').with_args('new-deployment', public_app=None, apps=[], name='boo', public_domain='other.path').once()

        r = yield controller.create('foo', 'foo.bar')
        assert isinstance(r, Deployment)
        assert r.public_domain == 'foo.bar'
        assert r.name == 'foo'

        r = yield controller.get('foo')
        assert r.public_domain == 'foo.bar'
        assert r.name == 'foo'

        r = yield controller.create('boo', 'other.path')
        assert isinstance(r, Deployment)
        assert r.public_domain == 'other.path'
        assert r.name == 'boo'

        r = yield controller.list()

        assert isinstance(r, list)
        assert len(r) == 2
        for app in r:
            assert isinstance(app, Deployment)

        eb.should_receive('fire_event').with_args('remove-deployment', name='foo').once()
        yield controller.remove('foo')

        with pytest.raises(DeploymentDoesNotExist):
            yield controller.get('foo')




@pytest.inlineCallbacks
def test_deployment_controller_new_app():

    redis = yield txredisapi.Connection(dbid=2)
    yield redis.flushdb()

    eb = flexmock()
    ac = flexmock()

    def configure(binder):
        binder.bind(txredisapi.Connection, redis)
        binder.bind(EventBus, eb)
        binder.bind(ApplicationController, ac)

    with inject_services(configure):
        controller = DeploymentController()

        eb.should_receive('fire_event').once()
        yield controller.create('foo', 'foo.bar')

        r = yield controller.get('foo')
        assert r.apps == []

        ac.should_receive('create').with_args('bar.foo', {'path': 'some/path'}, skip_validation=True).once()
        yield controller.new_app('foo', 'bar', {'path': 'some/path'}, skip_validation=True, skip_events=True)

        r = yield controller.get('foo')
        assert r.apps == ['bar.foo']

        yield controller.remove_app('foo', 'bar')

        r = yield controller.get('foo')
        assert r.apps == []





@pytest.inlineCallbacks
def test_deployment_controller_publish_app():

    redis = yield txredisapi.Connection(dbid=2)
    yield redis.flushdb()

    eb = flexmock()

    def configure(binder):
        binder.bind(txredisapi.Connection, redis)
        binder.bind(EventBus, eb)

    with inject_services(configure):
        controller = DeploymentController()

        eb.should_receive('fire_event').once()
        yield controller.create('foo', None)

        r = yield controller.get('foo')
        assert r.public_app is None

        yield controller.publish_app('foo', 'bar')

        r = yield controller.get('foo')
        assert r.public_app == 'bar.foo'

        yield controller.unpublish_app('foo')

        r = yield controller.get('foo')
        assert r.public_app is None


