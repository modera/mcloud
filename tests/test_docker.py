from contextlib import contextmanager
from flexmock import flexmock
import inject
import docker
from mfcloud.container import DockerLocal


@contextmanager
def real_docker():
    def configurator(binder):
        binder.bind_to_constructor(docker.Client, lambda: docker.Client(base_url='unix://var/run/docker.sock',
                                                                        version='1.6',
                                                                        timeout=10))
    inject.clear_and_configure(configurator)

    yield


@contextmanager
def mock_docker():
    mock = flexmock()
    inject.clear_and_configure(lambda binder: binder.bind(docker.Client, mock))

    yield mock


def test_docker_local():

    with real_docker():
        d = DockerLocal()

        assert isinstance(d.client, docker.Client)
        print d.client.info()

        assert d.client.info()['Driver'] == 'aufs', 'Drivers other than aufs are not tested'


def test_gen_wrapper():
    def gen():
        for x in range(1, 4):
            if x < 3:
                yield x
            else:
                raise ValueError()

    vals = [x for x in DockerLocal._gen_wrapper(gen())]

    assert vals == [1, 2]


def test_build_image_with_generator():

    with real_docker():
        d = DockerLocal()
        stream = DockerLocal._gen_wrapper(d.client.build(path='mfcloud/dns_locator', stream=True))

        for x in stream:
            print x
