import json
import logging
import inject
from mfcloud.config import YamlConfig, ConfigParseError
import os
from twisted.internet import defer, reactor
import txredisapi


class Application(object):

    def __init__(self, config):
        super(Application, self).__init__()

        self.config = config

    def load(self):

        if 'path' in self.config:
            yaml_config = YamlConfig(file=os.path.join(self.config['path'], 'mfcloud.yml'))
        elif 'source' in self.config:
            yaml_config = YamlConfig(source=self.config['source'])
        else:
            raise ConfigParseError('Can not load config.')

        yaml_config.load()

        d = defer.DeferredList([service.inspect() for service in yaml_config.get_services().values()])
        d.addCallback(lambda *result: yaml_config)
        return d


class AppDoesNotExist(Exception):
    pass


class ApplicationController(object):

    redis = inject.attr(txredisapi.Connection)

    def create(self, name, config):

        # validate first
        Application(config).load()

        d = self.redis.hset('mfcloud-apps', name, json.dumps(config))
        d.addCallback(lambda r: Application(config))

        return d

    def remove(self, name):
        return self.redis.hdel('mfcloud-apps', name)

    def get(self, name):

        d = self.redis.hget('mfcloud-apps', name)

        def ready(config):
            if not config:
                raise AppDoesNotExist('Application with name "%s" do not exist' % name)
            else:
                app = Application(json.loads(config))
                return app

        d.addCallback(ready)

        return d

    def list(self):
        d = self.redis.hgetall('mfcloud-apps')

        def ready(config):
            return dict([(name, Application(json.loads(config))) for name, config in config.items()])
        d.addCallback(ready)

        return d