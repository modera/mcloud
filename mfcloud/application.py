import inject
import txredisapi


class Application(object):

    def __init__(self, config_path):
        super(Application, self).__init__()

        self.config_path = config_path


class ApplicationController(object):

    redis = inject.attr(txredisapi.Connection)

    def create(self, name, path):
        self.redis.set('')

    def remove(self, name):
        pass

    def get(self, name):
        pass