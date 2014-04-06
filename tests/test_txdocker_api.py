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
def test_images_that_exist(client):

    result = yield client.images(name='base')
    assert 'base:latest' in result[0]['RepoTags']

@pytest.inlineCallbacks
def test_images_all(client):

    result = yield client.images()

    assert len(result) > 1

@pytest.inlineCallbacks
def test_build(client):

    builder = DockerfileImageBuilder(os.path.join(os.path.dirname(__file__), '_files/ct_bash'))

    d = builder.create_archive()

    def build_image(docker_file):
        return client.build_image(docker_file)

    d.addCallback(build_image)

    result = yield d

    assert re.match('^[0-9a-f]+$', result)
