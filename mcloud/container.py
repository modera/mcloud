from StringIO import StringIO
import logging
import tarfile
from abc import abstractmethod
import inject
from mcloud.txdocker import IDockerClient
from mcloud.util import Interface
from twisted.internet import reactor, defer


logger = logging.getLogger('mcloud.application')
from twisted.python import log

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

    @defer.inlineCallbacks
    def build_image(self, ticket_id):

        log.msg('[%s] Building image "%s".', ticket_id, self.image)

        name = self.image
        tag = None
        if ':' in name:
            name, tag = name.split(':')

        images = yield self.client.images(name=name)

        if tag:
            images = [x for x in images if self.image in x['RepoTags']]

        if not images:
            log.msg('[%s] Image is not there. Pulling "%s" ...', ticket_id, self.image)

            yield self.client.pull(name, ticket_id, tag)

        log.msg('[%s] Image "%s" is ready to use.', ticket_id, self.image)
        defer.returnValue(self.image)


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
            except OSError as e:
                d.errback(Exception('Can not access %s: %s' % (self.path, str(e))))
            except Exception as e:
                d.errback(e)
            finally:
                memfile.close()

        reactor.callLater(0, archive)
        return d

    @defer.inlineCallbacks
    def build_image(self, ticket_id):
        archive = yield self.create_archive()
        ret = yield self.client.build_image(archive, ticket_id=ticket_id)
        defer.returnValue(ret)


class ContainerBuider(IContainerBuilder):

    client = inject.attr(IDockerClient)




