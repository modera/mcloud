from flexmock import flexmock
from mfcloud.config import YamlConfig
from mfcloud.service import Service
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
