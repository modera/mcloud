from itertools import chain as generator
from flexmock import flexmock
import os
from mcloud.container import PrebuiltImageBuilder, DockerfileImageBuilder
from mcloud.test_utils import mock_docker
import pytest
from twisted.internet import defer


@pytest.inlineCallbacks
def test_image_builder_prebuilt():

    with mock_docker() as docker_mock:
        dm = docker_mock
        """@type : flexmock.Mock"""

        #dm.should_receive('images').with_args(name='foo/bar').and_return([])

        dm.should_receive('images').with_args(name='foo/bar').once().and_return(defer.succeed([]))
        dm.should_receive('pull').with_args(name='foo/bar', ticket_id=123123).once().and_return(defer.succeed(['foo', 'bar', 'baz']))

        builder = PrebuiltImageBuilder('foo/bar')

        result = yield builder.build_image(ticket_id=123123)
        assert result == 'foo/bar'

@pytest.inlineCallbacks
def test_image_builder_prebuilt_already_built():

    with mock_docker() as docker_mock:
        dm = docker_mock
        """@type : flexmock.Mock"""

        #dm.should_receive('images').with_args(name='foo/bar').and_return([])

        dm.should_receive('pull').never()
        dm.should_receive('images').with_args(name='foo/bar').once().and_return(defer.succeed([
          {
             "RepoTags": [
               "foo:bar",
             ],
             "Id": "8dbd9e392a964056420e5d58ca5cc376ef18e2de93b5cc90e868a1bbc8318c1c",
             "Created": 1365714795,
             "Size": 131506275,
             "VirtualSize": 131506275
          }
        ]))

        builder = PrebuiltImageBuilder('foo/bar')

        result = yield builder.build_image(ticket_id=123123)
        assert result == 'foo/bar'


@pytest.inlineCallbacks
def test_image_builder_create_archive():

    builder = DockerfileImageBuilder(os.path.join(os.path.dirname(__file__), '_files/ct_bash'))

    file = yield builder.create_archive()

    assert len(file) > 30


@pytest.inlineCallbacks
def test_image_builder_build():

    with mock_docker() as client:

        builder = DockerfileImageBuilder(os.path.join(os.path.dirname(__file__), '_files/ct_bash'))

        flexmock(builder)

        builder.should_receive('create_archive').once().and_return(defer.succeed('foo'))

        client.should_receive('build_image').with_args('foo', ticket_id=123123).and_return(defer.succeed('baz'))

        result = yield builder.build_image(ticket_id=123123)

        assert result == 'baz'



