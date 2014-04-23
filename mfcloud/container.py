from StringIO import StringIO
import logging
import tarfile
from abc import abstractmethod
import inject
from mfcloud.txdocker import IDockerClient
from mfcloud.util import Interface
from twisted.internet import reactor, defer


logger = logging.getLogger('mfcloud.application')

class IContainerBuilder(Interface):
    pass


class IImageBuilder(Interface):

    client = inject.attr(IDockerClient)
    """
    @type client: DockerTwistedClient
    """

    @abstractmethod
    def build_image(self, ticket_id):
        pass


class PrebuiltImageBuilder(IImageBuilder):
    def __init__(self, image):
        super(PrebuiltImageBuilder, self).__init__()

        self.image = image

    def build_image(self, ticket_id):

        logger.debug('[%s] Building image "%s".', ticket_id, self.image)

        def on_ready(images):
            if not images:
                logger.debug('[%s] Image is not there. Pulling "%s" ...', ticket_id, self.image)
                d_pull = self.client.pull(self.image, ticket_id)
                d_pull.addCallback(lambda *args: self.image)
                return d_pull
            else:
                logger.debug('[%s] Image "%s" is ready to use.', ticket_id, self.image)
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
            return self.client.build_image(archive, ticket_id=ticket_id)

        d.addCallback(on_archive_ready)

        return d


class ContainerBuider(IContainerBuilder):

    client = inject.attr(IDockerClient)




