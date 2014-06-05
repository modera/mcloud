from collections import defaultdict
import json
import logging
import inject
from mfcloud.config import YamlConfig, ConfigParseError
import os
from twisted.internet import defer, reactor
import txredisapi


class Application(object):

    dns_search_suffix = inject.attr('dns-search-suffix')
    host_ip = inject.attr('host_ip')

    def __init__(self, config, name=None, public_url=None):
        super(Application, self).__init__()

        self.config = config
        self.name = name
        self.public_url = public_url

    def load(self, need_details=False):

        try:
            if 'path' in self.config:
                yaml_config = YamlConfig(file=os.path.join(self.config['path'], 'mfcloud.yml'), app_name=self.name)
            elif 'source' in self.config:
                yaml_config = YamlConfig(source=self.config['source'], app_name=self.name)
            else:
                raise ConfigParseError('Can not load config.')

            yaml_config.load()
        except ValueError as e:
            return defer.succeed({
                'name': self.name,
                'config': self.config,
                'host_ip': self.host_ip,
                'services': [],
                'running': False,
                'status': 'error',
                'message': '%s When loading config: %s' % (e.message, self.config)
            })

        def on_loaded(app_config):

            is_running = True
            status = 'RUNNING'

            web_ip = None
            web_service = None

            services = []
            for service in app_config.get_services().values():
                services.append({
                    'name': service.name,
                    'ip': service.ip(),
                    'started_at': service.started_at(),
                    'fullname': '%s.%s' % (service.name, self.dns_search_suffix),
                    'is_web': service.is_web(),
                    'running': service.is_running(),
                    'created': service.is_created(),
                })

                if service.is_web():
                    web_ip = service.ip()
                    web_service = service.name

                if not service.is_running():
                    is_running = False
                    status = 'STOPPED'

            return {
                'name': self.name,
                'fullname': '%s.%s' % (self.name, self.dns_search_suffix),
                'web_ip': web_ip,
                'web_service': web_service,
                'public_url': self.public_url,
                'config': self.config,
                'services': services,
                'running': is_running,
                'status': status
            }



        d = defer.DeferredList([service.inspect() for service in yaml_config.get_services().values()])
        d.addCallback(lambda *result: yaml_config)

        if need_details:
            d.addCallback(on_loaded)

        return d


class AppDoesNotExist(Exception):
    pass


class ApplicationController(object):

    redis = inject.attr(txredisapi.Connection)

    def create(self, name, config, skip_validation=False):

        # validate first
        if not skip_validation:
            Application(config).load()

        d = self.redis.hset('mfcloud-apps', name, json.dumps(config))
        d.addCallback(lambda r: Application(config, name=name))

        return d

    def update(self, name, config):

        d = self.redis.hget('mfcloud-apps', name)

        def on_load(data):
            data.update(config)
            return self.redis.hset('mfcloud-apps', name, json.dumps(data))

        d.addCallback(on_load)
        return d

    def remove(self, name):
        return self.redis.hdel('mfcloud-apps', name)

    def get(self, name):

        d = self.redis.hget('mfcloud-apps', name)

        def ready(config):
            if not config:
                raise AppDoesNotExist('Application with name "%s" do not exist' % name)
            else:
                app = Application(json.loads(config), name=name)
                return app

        d.addCallback(ready)

        return d

    def list(self, *args):
        d = self.redis.hgetall('mfcloud-apps')

        def ready(config):

            dd = self.redis.hgetall('mfcloud-deployments')

            def dep_ready(deps):
                pub_apps = {}
                for name, config_raw in deps.items():
                    try:
                        dep = json.loads(config_raw)
                        if dep['public_app']:
                            pub_apps[dep['public_app']] = dep['public_domain']
                    except ValueError:
                        pass

                return defer.gatherResults([(Application(json.loads(app_config), name=name, public_url=(pub_apps[name] if name in pub_apps else None))).load(need_details=True)
                                        for name, app_config in config.items()], consumeErrors=True)

            dd.addCallback(dep_ready)
            return dd



        d.addCallback(ready)
        return d