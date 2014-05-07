from flexmock import flexmock
from mfcloud.application import Application, ApplicationController, AppDoesNotExist
from mfcloud.config import YamlConfig
from mfcloud.container import DockerfileImageBuilder, PrebuiltImageBuilder
from mfcloud.service import Service
from mfcloud.test_utils import real_docker
from mfcloud.util import inject_services
import os
import pytest
import txredisapi


def test_new_app_instance():

    app = Application({'path': 'foo/bar'})
    assert app.config['path'] == 'foo/bar'

@pytest.inlineCallbacks
def test_app_load():

    with real_docker():
        app = Application({'path': os.path.realpath(os.path.dirname(__file__) + '/../')})
        config = yield app.load()

        assert isinstance(config, YamlConfig)
        assert len(config.get_services()) == 1

        service = config.get_services()['controller']
        assert isinstance(service, Service)
        assert isinstance(service.image_builder, DockerfileImageBuilder)

        assert service.is_inspected()

@pytest.inlineCallbacks
def test_app_load_source():

    with real_docker():
        app = Application({'source': '''
controller:
  image: foo/bar
'''})

        config = yield app.load()

        assert isinstance(config, YamlConfig)
        assert len(config.get_services()) == 1

        service = config.get_services()['controller']
        assert isinstance(service, Service)
        assert isinstance(service.image_builder, PrebuiltImageBuilder)

        assert service.is_inspected()


@pytest.inlineCallbacks
def test_app_controller():

    redis = yield txredisapi.Connection(dbid=2)
    yield redis.flushdb()

    def configure(binder):
        binder.bind(txredisapi.Connection, redis)

    with inject_services(configure):
        controller = ApplicationController()

        with pytest.raises(AppDoesNotExist):
            yield controller.get('foo')

        r = yield controller.create('foo', {'path': 'some/path'})
        assert isinstance(r, Application)
        assert r.config['path'] == 'some/path'

        r = yield controller.get('foo')
        assert isinstance(r, Application)
        assert r.config['path'] == 'some/path'

        r = yield controller.create('boo', {'path': 'other/path'})
        assert isinstance(r, Application)
        assert r.config['path'] == 'other/path'

        r = yield controller.list()

        assert isinstance(r, dict)
        assert len(r) == 2
        for app in r.values():
            assert isinstance(app, Application)

        yield controller.remove('foo')

        with pytest.raises(AppDoesNotExist):
            yield controller.get('foo')

