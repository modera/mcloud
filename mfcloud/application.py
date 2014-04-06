import json
import inject
import txredisapi


class Application(object):

    def __init__(self, config):
        super(Application, self).__init__()

        self.config = config


class ApplicationController(object):

    redis = inject.attr(txredisapi.Connection)

    def create(self, name, path):
        config = {'path': path}

        d = self.redis.hset('mfcloud-apps', name, json.dumps(config))
        d.addCallback(lambda r: Application(config))

        return d

    def remove(self, name):
        return self.redis.hdel('mfcloud-apps', name)

    def get(self, name):

        d = self.redis.hget('mfcloud-apps', name)

        def ready(config):
            if not config:
                return None
            else:
                return Application(json.loads(config))
        d.addCallback(ready)

        return d

    def list(self):
        d = self.redis.hgetall('mfcloud-apps')

        def ready(config):
            return dict([(name, Application(json.loads(config))) for name, config in config.items()])
        d.addCallback(ready)

        return d