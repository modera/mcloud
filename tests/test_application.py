from mfcloud.application import Application, ApplicationController
from mfcloud.util import inject_services
import pytest
import txredisapi


def test_new_app_instance():

    app = Application({'path': 'foo/bar'})

    assert app.config['path'] == 'foo/bar'


@pytest.inlineCallbacks
def test_app_controller():

    redis = yield txredisapi.Connection(dbid=2)
    yield redis.flushdb()

    def configure(binder):
        binder.bind(txredisapi.Connection, redis)

    with inject_services(configure):
        controller = ApplicationController()

        r = yield controller.get('foo')
        assert r is None

        r = yield controller.create('foo', 'some/path')
        assert isinstance(r, Application)
        assert r.config['path'] == 'some/path'

