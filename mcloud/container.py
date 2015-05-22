from StringIO import StringIO
import logging
import tarfile
from tempfile import mkdtemp
from abc import abstractmethod
from mcloud.util import Interface
from twisted.internet import reactor, defer

logger = logging.getLogger('mcloud.application')
from twisted.python import log



class IContainerBuilder(Interface):
    pass


class IImageBuilder(Interface):

    @abstractmethod
    def build_image(self, ticket_id, service):
        pass


class PrebuiltImageBuilder(IImageBuilder):
    def __init__(self, image):
        super(PrebuiltImageBuilder, self).__init__()

        self.image = image

    @defer.inlineCallbacks
    def build_image(self, ticket_id, service):

        log.msg('[%s] Building image "%s".', ticket_id, self.image)

        name = self.image
        tag = None
        if ':' in name:
            name, tag = name.split(':')

        images = yield service.client.images(name=name)

        if tag:
            images = [x for x in images if self.image in x['RepoTags']]

        if not images:
            log.msg('[%s] Image is not there. Pulling "%s" ...', ticket_id, self.image)

            yield service.client.pull(name, ticket_id, tag)

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
    def build_image(self, ticket_id, service):
        archive = yield self.create_archive()
        ret = yield service.client.build_image(archive, ticket_id=ticket_id)
        defer.returnValue(ret)


class InlineDockerfileImageBuilder(DockerfileImageBuilder):
    def __init__(self, source):
        self.source = source

        super(InlineDockerfileImageBuilder, self).__init__(None)

        self.image_id = None

    def build_image(self, ticket_id, service):

        tdir = mkdtemp()
        with open(tdir + '/Dockerfile', 'w+') as f:
            f.write(self.source)

        self.path = tdir

        return super(InlineDockerfileImageBuilder, self).build_image(ticket_id, service)






