from abc import abstractmethod
import docker
import inject
from mfcloud.txdocker import IDockerClient
from mfcloud.util import Interface


class IContainerBuilder(Interface):
    pass


class IImageBuilder(Interface):

    client = inject.attr(IDockerClient)

    @abstractmethod
    def build_image(self):
        pass

    @abstractmethod
    def get_image_name(self):
        pass


class PrebuiltImageBuilder(IImageBuilder):
    def __init__(self, image):
        super(PrebuiltImageBuilder, self).__init__()

        self.image = image

    def build_image(self):

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

    def get_image_name(self):
        return self.image


class DockerfileImageBuilder(IImageBuilder):
    def __init__(self, path):
        super(DockerfileImageBuilder, self).__init__()
        self.path = path

        self.image_id = None

    def build_image(self):
        out = self.client.build(self.path)

        self.image_id = out.next()  # first line is image id beeing built

        return out

    def get_image_name(self):
        return self.image_id


class ContainerBuider(IContainerBuilder):

    client = inject.attr(IDockerClient)




