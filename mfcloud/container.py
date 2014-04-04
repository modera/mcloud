import docker
import inject
from mfcloud.api import IDocker

class DockerLocal(IDocker):

    client = inject.attr(docker.Client)

    @classmethod
    def _gen_wrapper(self, subgenerator):
        try:
            for x in subgenerator:

                yield x
        except ValueError:
            pass

