import sys
from _pytest.runner import Exit
from flexmock import flexmock
from mfcloud.application import Application, ApplicationController, AppDoesNotExist
from mfcloud.config import YamlConfig
from mfcloud.container import DockerfileImageBuilder, PrebuiltImageBuilder
from mfcloud.service import Service
from mfcloud.test_utils import real_docker
from mfcloud.txdocker import IDockerClient, DockerTwistedClient
from mfcloud.util import inject_services, txtimeout
import os
import pytest
from twisted.internet import reactor, defer
import txredisapi


def test_new_app_instance():

    app = Application({'path': 'foo/bar'}, name='foo')
    assert app.config['path'] == 'foo/bar'
    assert app.name == 'foo'

@pytest.inlineCallbacks
def test_app_load():


    def timeout():
        print('Can not connect to redis!')
        reactor.stop()

    redis = yield txtimeout(txredisapi.Connection(dbid=2), 2, timeout)
    yield redis.flushdb()


    def configure(binder):
        binder.bind(txredisapi.Connection, redis)
        binder.bind(IDockerClient, DockerTwistedClient())

    with inject_services(configure):
        app = Application({'path': os.path.realpath(os.path.dirname(__file__) + '/../')}, name='myapp')
        config = yield app.load()

        assert isinstance(config, YamlConfig)
        assert len(config.get_services()) == 1
        assert config.app_name == 'myapp'

        service = config.get_services()['controller.myapp']
        assert isinstance(service, Service)
        assert isinstance(service.image_builder, DockerfileImageBuilder)

        assert service.is_inspected()

@pytest.inlineCallbacks
def test_app_load_source():


    def timeout():
        print('Can not connect to redis!')
        reactor.stop()

    redis = yield txtimeout(txredisapi.Connection(dbid=2), 2, timeout)
    yield redis.flushdb()


    def configure(binder):
        binder.bind(txredisapi.Connection, redis)
        binder.bind(IDockerClient, DockerTwistedClient())

    with inject_services(configure):
        app = Application({'source': '''
controller:
  image: foo/bar
'''}, name='myapp')

        config = yield app.load()

        assert isinstance(config, YamlConfig)
        assert len(config.get_services()) == 1
        assert config.app_name == 'myapp'

        service = config.get_services()['controller.myapp']
        assert isinstance(service, Service)
        assert isinstance(service.image_builder, PrebuiltImageBuilder)

        assert service.is_inspected()


@pytest.inlineCallbacks
def test_app_controller():

    def timeout():
        print('Can not connect to redis!')
        reactor.stop()

    redis = yield txtimeout(txredisapi.Connection(dbid=2), 2, timeout)
    yield redis.flushdb()


    def configure(binder):
        binder.bind(txredisapi.Connection, redis)

    with inject_services(configure):
        controller = ApplicationController()

        with pytest.raises(AppDoesNotExist):
            yield controller.get('foo')

        r = yield controller.create('foo', {'path': 'some/path'}, skip_validation=True)
        assert isinstance(r, Application)
        assert r.name == 'foo'
        assert r.config['path'] == 'some/path'

        r = yield controller.get('foo')
        assert isinstance(r, Application)
        assert r.name == 'foo'
        assert r.config['path'] == 'some/path'

        r = yield controller.create('boo', {'path': 'other/path'}, skip_validation=True)
        assert isinstance(r, Application)
        assert r.name == 'boo'
        assert r.config['path'] == 'other/path'

        mockapp = flexmock()
        flexmock(Application).new_instances(mockapp)
        mockapp.should_receive('load').with_args(need_details=True).and_return(defer.succeed({'foo': 'bar'}))

        r = yield controller.list()

        assert isinstance(r, list)
        assert len(r) == 2
        for app in r:
            assert app == {'foo': 'bar'}

        yield controller.remove('foo')

        with pytest.raises(AppDoesNotExist):
            yield controller.get('foo')

