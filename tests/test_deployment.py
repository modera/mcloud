from mfcloud.deployment import Deployment, DeploymentController, DeploymentDoesNotExist
from mfcloud.util import inject_services
import pytest
import txredisapi


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

    def configure(binder):
        binder.bind(txredisapi.Connection, redis)

    with inject_services(configure):
        controller = DeploymentController()

        with pytest.raises(DeploymentDoesNotExist):
            yield controller.get('foo')

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

        assert isinstance(r, dict)
        assert len(r) == 2
        for app in r.values():
            assert isinstance(app, Deployment)

        yield controller.remove('foo')

        with pytest.raises(DeploymentDoesNotExist):
            yield controller.get('foo')




@pytest.inlineCallbacks
def test_deployment_controller_new_app():

    redis = yield txredisapi.Connection(dbid=2)
    yield redis.flushdb()

    def configure(binder):
        binder.bind(txredisapi.Connection, redis)

    with inject_services(configure):
        controller = DeploymentController()

        yield controller.create('foo', 'foo.bar')

        r = yield controller.get('foo')
        assert r.apps == []

        yield controller.new_app('foo', 'bar', 'some/path')

        r = yield controller.get('foo')
        assert r.apps == ['bar.foo']

        yield controller.remove_app('foo', 'bar')

        r = yield controller.get('foo')
        assert r.apps == []
