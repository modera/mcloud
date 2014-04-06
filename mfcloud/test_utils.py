from decorator import contextmanager
from flexmock import flexmock
import inject
from mfcloud.txdocker import IDockerClient, DockerTwistedClient


@contextmanager
def real_docker():
    def configurator(binder):
        binder.bind_to_constructor(IDockerClient, lambda: DockerTwistedClient())
    inject.clear_and_configure(configurator)

    yield


@contextmanager
def mock_docker():
    mock = flexmock(DockerTwistedClient())
    inject.clear_and_configure(lambda binder: binder.bind(IDockerClient, mock))

    yield mock


