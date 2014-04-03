


class Service(object):
    image_builder = None
    name = None
    volumes = None
    command = None
    env = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        super(Service, self).__init__()




