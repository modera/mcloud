import os
from flexmock import flexmock
from mfcloud.config import YamlConfig
from mfcloud.container import DockerfileImageBuilder
from mfcloud.service import Service
from mfcloud.test_utils import real_docker
import pytest
from twisted.internet import defer


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
    s._inspect_data = {'foo': 'bar'}

    assert s.is_inspected() is True


def test_not_inspected():

    s = Service()
    assert s.is_inspected() is False


@pytest.inlineCallbacks
def test_service_api():

    with real_docker():

        name = 'test.foo'

        s = Service(
            image_builder=DockerfileImageBuilder(os.path.join(os.path.dirname(__file__), '_files/ct_bash')),
            name=name
        )

        r = yield s.is_created()
        assert r is False

        r = yield s.is_running()
        assert r is False

        r = yield s.create(ticket_id=123123)
        assert 'Id' in r

        r = yield s.is_created()
        assert r is True

        r = yield s.is_running()
        assert r is False


        r = yield s.start(ticket_id=123123)
        assert r is True

        r = yield s.is_created()
        assert r is True

        r = yield s.is_running()
        assert r is True

        r = yield s.stop(ticket_id=123123)
        assert r is True

        r = yield s.is_created()
        assert r is True

        r = yield s.is_running()
        assert r is False

        r = yield s.destroy(ticket_id=123123)
        assert r is True

        r = yield s.is_created()
        assert r is False

        r = yield s.is_running()
        assert r is False
