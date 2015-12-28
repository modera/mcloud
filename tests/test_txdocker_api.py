import json
from mcloud.attach import attach_to_container
import os
from flexmock import flexmock
from mcloud import txhttp
from mcloud.container import DockerfileImageBuilder
from mcloud.test_utils import real_docker
from mcloud.txdocker import DockerTwistedClient, get_environ_docker
import pytest
import re
from twisted.internet import defer

@pytest.fixture
def client():
    with real_docker():
        client = get_environ_docker()
        return client


@pytest.inlineCallbacks
def test_images(client):

    result = yield client.images(name='image_that_do_not_exist_ever_326782387')
    assert result == []

@pytest.inlineCallbacks
def test_images_that_exist(client):

    result = yield client.images(name='ubuntu')
    assert result[0]['RepoTags'][0].startswith('ubuntu:')

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
