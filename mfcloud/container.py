from abc import abstractmethod
import docker
import inject
from mfcloud.util import Interface


class IDocker(Interface):
    pass


class IImageBuilder(Interface):

    client = inject.attr(docker.Client)

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

        if not self.client.images(name=self.image):
            return self.client.pull(name=self.image, stream=True)

        return ()

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


class DockerLocal(IDocker):
    client = inject.attr(docker.Client)

    @classmethod
    def _gen_wrapper(self, subgenerator):
        try:
            for x in subgenerator:

                yield x
        except ValueError:
            pass

    def build_image(self):
        pass

