import json
from mfcloud.attach import attach_to_container
import os
from flexmock import flexmock
from mfcloud import txhttp
from mfcloud.container import DockerfileImageBuilder
from mfcloud.test_utils import real_docker
from mfcloud.txdocker import DockerTwistedClient
import pytest
import re
from twisted.internet import defer

@pytest.fixture
def client():
    with real_docker():
        client = DockerTwistedClient()
        return client


@pytest.inlineCallbacks
def test_images(client):

    result = yield client.images(name='image_that_do_not_exist_ever_326782387')
    assert result == []

@pytest.inlineCallbacks
def test_attach(client):

    yield attach_to_container('a478')
    # def on_log(data):
    #     print(data)
    # result = yield client.attach('a478')
    # result = yield client.attach('1a1')

    # print result

@pytest.inlineCallbacks
def test_images_that_exist(client):

    result = yield client.images(name='base')
    assert 'base:latest' in result[0]['RepoTags']

@pytest.inlineCallbacks
def test_images_all(client):

    result = yield client.images()

    assert len(result) > 1

@pytest.inlineCallbacks
@pytest.mark.xfail
def test_build(client):

    class Publisher(object):

        def __init__(self):
            self.called = 0

        def publish(self, data, tag):
            assert tag == 'log-123123'
            assert len(data) > 0

            self.called += 1

    client.message_publisher = Publisher()

    builder = DockerfileImageBuilder(os.path.join(os.path.dirname(__file__), '_files/ct_bash'))

    d = builder.create_archive()

    def build_image(docker_file):
        return client.build_image(docker_file, ticket_id=123123)

    d.addCallback(build_image)

    result = yield d

    assert re.match('^[0-9a-f]+$', result)

    assert client.message_publisher.called > 0
