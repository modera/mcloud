from flexmock import flexmock
from mfcloud.deployment import Deployment, DeploymentController, DeploymentDoesNotExist
from mfcloud.events import EventBus
from mfcloud.util import inject_services
import pytest
import txredisapi
from txzmq import ZmqPubConnection


def test_deployment_new_instance():

    d = Deployment(public_domain='foo.bar', name='baz', apps=['v1.baz', 'v1.baz'])

    assert d.name == 'baz'
    assert d.public_domain == 'foo.bar'

    assert len(d.apps) == 2
    assert d.apps == ['v1.baz', 'v1.baz']

    assert d.config == {
        'name': 'baz',
        'public_domain': 'foo.bar',
        'apps': ['v1.baz', 'v1.baz'],
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

        eb.should_receive('fire_event').with_args('new-deployment', apps=[], name='foo', public_domain='foo.bar').once()
        eb.should_receive('fire_event').with_args('new-deployment', apps=[], name='boo', public_domain='other.path').once()

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

    def configure(binder):
        binder.bind(txredisapi.Connection, redis)
        binder.bind(EventBus, eb)

    with inject_services(configure):
        controller = DeploymentController()

        eb.should_receive('fire_event').once()
        yield controller.create('foo', 'foo.bar')

        r = yield controller.get('foo')
        assert r.apps == []

        yield controller.new_app('foo', 'bar', 'some/path')

        r = yield controller.get('foo')
        assert r.apps == ['bar.foo']

        yield controller.remove_app('foo', 'bar')

        r = yield controller.get('foo')
        assert r.apps == []
