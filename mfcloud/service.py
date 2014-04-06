


class Service(object):
    image_builder = None
    name = None
    volumes = None
    command = None
    env = None
    config = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        super(Service, self).__init__()

    def build_docker_config(self):
        pass




