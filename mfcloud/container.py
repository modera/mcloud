from StringIO import StringIO
import tarfile
from abc import abstractmethod
import inject
from mfcloud.txdocker import IDockerClient
from mfcloud.util import Interface
from twisted.internet import reactor, defer


class IContainerBuilder(Interface):
    pass


class IImageBuilder(Interface):

    client = inject.attr(IDockerClient)

    @abstractmethod
    def build_image(self, ticket_id):
        pass


class PrebuiltImageBuilder(IImageBuilder):
    def __init__(self, image):
        super(PrebuiltImageBuilder, self).__init__()

        self.image = image

    def build_image(self, ticket_id):

        def on_ready(images):
            if not images:
                d_pull = self.client.pull(name=self.image)
                d_pull.addCallback(lambda *args: self.image)
                return d_pull
            else:
                return self.image

        d = self.client.images(name=self.image)
        d.addCallback(on_ready)

        return d


class DockerfileImageBuilder(IImageBuilder):
    def __init__(self, path):
        super(DockerfileImageBuilder, self).__init__()
        self.path = path

        self.image_id = None

    def create_archive(self):
        d = defer.Deferred()

        def archive():
            memfile = StringIO()
            try:
                t = tarfile.open(mode='w', fileobj=memfile)
                t.add(self.path, arcname='.')
                d.callback(memfile.getvalue())
            finally:
                memfile.close()

        reactor.callLater(0, archive)
        return d

    def build_image(self, ticket_id):

        d = self.create_archive()

        def on_archive_ready(archive):
            return self.client.build_image(archive, ticket_id=123123)

        d.addCallback(on_archive_ready)

        return d


class ContainerBuider(IContainerBuilder):

    client = inject.attr(IDockerClient)




