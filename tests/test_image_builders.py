from itertools import chain as generator
from mfcloud.container import PrebuiltImageBuilder, DockerfileImageBuilder
from mfcloud.util import mock_docker


def test_image_builder_prebuilt():

    with mock_docker() as docker_mock:
        dm = docker_mock
        """@type : flexmock.Mock"""

        #dm.should_receive('images').with_args(name='foo/bar').and_return([])

        dm.should_receive('images').with_args(name='foo/bar').once().and_return([])
        dm.should_receive('pull').with_args(name='foo/bar', stream=True).once().and_return(generator(['foo', 'bar', 'baz']))

        builder = PrebuiltImageBuilder('foo/bar')

        assert [x for x in builder.build_image()] == ['foo', 'bar', 'baz']

        assert builder.get_image_name() == 'foo/bar'


def test_image_builder_build():

    with mock_docker() as docker_mock:
        dm = docker_mock
        """@type : flexmock.Mock"""

        dm.should_receive('build').with_args('/foo/bar').and_return(generator([
            'eec8980ee833',
            'Step 0 : FROM ubuntu',
            'Step 1 : RUN hello',
        ]))
        #dm.should_receive('images').with_args(name='foo/bar').and_return([])

        builder = DockerfileImageBuilder('/foo/bar')

        assert [x for x in builder.build_image()] == ['Step 0 : FROM ubuntu', 'Step 1 : RUN hello']

        assert builder.get_image_name() == 'eec8980ee833'



