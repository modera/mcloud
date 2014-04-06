from itertools import chain as generator
from mfcloud.container import PrebuiltImageBuilder, DockerfileImageBuilder
from mfcloud.test_utils import mock_docker
import pytest
from twisted.internet import defer


@pytest.inlineCallbacks
def test_image_builder_prebuilt():

    with mock_docker() as docker_mock:
        dm = docker_mock
        """@type : flexmock.Mock"""

        #dm.should_receive('images').with_args(name='foo/bar').and_return([])

        dm.should_receive('images').with_args(name='foo/bar').once().and_return(defer.succeed([]))
        dm.should_receive('pull').with_args(name='foo/bar').once().and_return(defer.succeed(['foo', 'bar', 'baz']))

        builder = PrebuiltImageBuilder('foo/bar')

        result = yield builder.build_image()
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

        result = yield builder.build_image()
        assert result == 'foo/bar'

#
# def test_image_builder_build():
#
#     with mock_docker() as docker_mock:
#         dm = docker_mock
#         """@type : flexmock.Mock"""
#
#         dm.should_receive('build').with_args('/foo/bar').and_return(generator([
#             'eec8980ee833',
#             'Step 0 : FROM ubuntu',
#             'Step 1 : RUN hello',
#         ]))
#         #dm.should_receive('images').with_args(name='foo/bar').and_return([])
#
#         builder = DockerfileImageBuilder('/foo/bar')
#
#         assert [x for x in builder.build_image()] == ['Step 0 : FROM ubuntu', 'Step 1 : RUN hello']
#
#         assert builder.get_image_name() == 'eec8980ee833'



