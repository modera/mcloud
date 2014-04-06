from mfcloud.util import Interface


class IDockerClient(Interface):
    pass


class DockerTwistedClient(object):

    def images(self, name=None):
        pass

    def pull(self, name=None):
        pass