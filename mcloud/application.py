import json

from mcloud.deployment import DeploymentController, Deployment
from mcloud.txdocker import DockerTwistedClient, DockerConnectionFailed
import re
import inject
from mcloud.config import YamlConfig, ConfigParseError
import os
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks
import txredisapi


class Application(object):
    deployment_controller = inject.attr(DeploymentController)

    APP_REGEXP = '[a-z0-9\-_]+'
    SERVICE_REGEXP = '[a-z0-9\-_]+'

    dns_search_suffix = inject.attr('dns-search-suffix')
    #host_ip = inject.attr('host_ip')

    def __init__(self, config, name=None, public_urls=None):
        super(Application, self).__init__()

        self.config = config
        self.name = name
        self.public_urls = public_urls or []
        self.client = None

        self.error = None

        self.deployment = None

    def get_env(self):
        if 'env' in self.config and self.config['env']:
            env = self.config['env']
        else:
            env = 'dev'
        return env

    @defer.inlineCallbacks
    def get_deployment(self):
        if self.deployment:
            defer.returnValue(self.deployment)

        if 'deployment' in self.config and self.config['deployment']:
            deployment_name = self.config['deployment']
            self.deployment = yield self.deployment_controller.get(deployment_name)
        else:
            self.deployment = yield self.deployment_controller.get_default()

        # no deployments at all
        if not self.deployment:
            self.deployment = Deployment(name='local')

        defer.returnValue(self.deployment)


    @defer.inlineCallbacks
    def load(self, need_details=False):

        try:
            if 'source' in self.config:
                yaml_config = YamlConfig(source=self.config['source'], app_name=self.name, path=self.config['path'], env=self.get_env())
            elif 'path' in self.config:
                yaml_config = YamlConfig(file=os.path.join(self.config['path'], 'mcloud.yml'), app_name=self.name, path=self.config['path'])
            else:
                self.error = {
                    'msg': 'Can not parse config'
                }
                defer.returnValue(None)

            deployment = yield self.get_deployment()
            if not deployment:
                self.error = {
                    'msg': 'No deployment found'
                }

            client = deployment.get_client()

            yield yaml_config.load(client=client)


            
            yield defer.gatherResults([service.inspect() for service in yaml_config.get_services().values()])


            if need_details:
                defer.returnValue(self._details(yaml_config))
            else:
                defer.returnValue(yaml_config)

        except ValueError as e:
            config_ = {'name': self.name, 'config': self.config, 'services': [], 'running': False, 'status': 'error',
                       'message': '%s When loading config: %s' % (e.message, self.config)}
            defer.returnValue(config_)



    def _details(self, app_config):
        is_running = True
        status = 'RUNNING'
        errors = []

        web_ip = None
        web_port = None
        web_target = None
        web_service = None

        ssl_ip = None
        ssl_port = None
        ssl_target = None
        ssl_service = None

        services = []
        for service in app_config.get_services().values():
            service.app_name = self.name
            services.append({
                'shortname': service.shortname,
                'name': service.name,
                'ip': service.ip(),
                'error': service.error,
                'ports': service.public_ports(),
                'hosts_path': service.hosts_path(),
                'volumes': service.attached_volumes(),
                'started_at': service.started_at(),
                'fullname': '%s.%s' % (service.name, self.dns_search_suffix),
                'is_web': service.is_web(),
                'running': service.is_running(),
                'created': service.is_created(),
                'cpu': service.cpu_usage,
                'memory': service.memory_usage,
            })

            if service.is_running():

                if service.is_web():
                    web_ip = service.ip()
                    web_port = service.get_web_port()
                    web_target = '%s:%s' % (service.ip(), service.get_web_port())
                    web_service = service.name

                if service.is_ssl():
                    ssl_ip = service.ip()
                    ssl_port = service.get_ssl_port()
                    ssl_target = '%s:%s' % (service.ip(), service.get_ssl_port())
                    ssl_service = service.name

            else:
                is_running = False

                if not service.error:
                    status = 'STOPPED'
                else:
                    status = 'error'
                    errors.append('%s: %s' % (service.name, service.error))

        return {
            'name': self.name,
            'hosts': app_config.hosts,
            'volumes': app_config.get_volumes(),
            'fullname': '%s.%s' % (self.name, self.dns_search_suffix),
            'web_ip': web_ip,
            'web_port': web_port,
            'web_target': web_target,
            'web_service': web_service,
            'ssl_ip': ssl_ip,
            'ssl_port': ssl_port,
            'ssl_target': ssl_target,
            'ssl_service': ssl_service,
            'public_urls': self.public_urls,
            'config': self.config,
            'services': services,
            'running': is_running,
            'status': status,
            'errors': errors,
        }


class AppDoesNotExist(Exception):
    pass


class ApplicationController(object):

    redis = inject.attr(txredisapi.Connection)

    def __init__(self):
        super(ApplicationController, self).__init__()

        self.internal_containers = []

    def mark_internal(self, container_id):
        if not container_id in self.internal_containers:
            self.internal_containers.append(container_id)

    def is_internal(self, container_id):
        return container_id in self.internal_containers



    @defer.inlineCallbacks
    def create(self, name, config, skip_validation=False, deployment=None):

        if not re.match('^%s$' % Application.APP_REGEXP, name):
            raise ValueError('Invalid name of application. Should be %s' % Application.APP_REGEXP)

        # validate first by crating application instance
        if not skip_validation:
            ret = yield Application(config).load()

        #  set data to redis. we don't care too much about result
        ret = yield self.redis.hset('mcloud-apps', name, json.dumps(config))
        defer.returnValue(Application(config, name=name))

    @defer.inlineCallbacks
    def update_source(self, name, source=None, skip_validation=False, env=None):

        app = yield self.get(name)
        if source:
            app.config.update({'source': source})

        if env:
            app.config.update({'env': env})

        # validate first by crating application instance
        if not skip_validation:
            ret = yield Application(app.config).load()

        #  set data to redis. we don't care too much about result
        ret = yield self.redis.hset('mcloud-apps', name, json.dumps(app.config))
        defer.returnValue(Application(app.config, name=name))

    @defer.inlineCallbacks
    def update(self, name, config):

        data = yield self.redis.hget('mcloud-apps', name)
        data = json.loads(data)
        data.update(config)
        ret = yield self.redis.hset('mcloud-apps', name, json.dumps(data))

        defer.returnValue(ret)

    @defer.inlineCallbacks
    def remove(self, name):
        ret = yield self.redis.hdel('mcloud-apps', name)
        defer.returnValue(ret)

    @defer.inlineCallbacks
    def load_app_config(self, config):
        cfg = json.loads(config)
        if not 'deployment' in cfg:
            cfg['deployment'] = yield self.redis.get('mcloud-deployment-default')

        defer.returnValue(cfg)

    @defer.inlineCallbacks
    def get(self, name):
        """
        Return application instance by it's name
        """
        config = yield self.redis.hget('mcloud-apps', name)

        if not config:
            raise AppDoesNotExist('Application with name "%s" do not exist' % name)
        else:
            cfg = yield self.load_app_config(config)

            defer.returnValue(Application(cfg, name=name))

    @defer.inlineCallbacks
    def volume_list(self, *args):

        config = yield self.redis.hgetall('mcloud-apps')

        result = {}

        for name, app_config in config.items():
            app = Application(json.loads(app_config), name=name)
            app = yield app.load(need_details=False)

            for service in app.services:
                result[service.name] = service.volumes

        defer.returnValue(result)

    @defer.inlineCallbacks
    def ip_list(self, *args):

        config = yield self.redis.hgetall('mcloud-apps')

        result = {}

        for name, app_config in config.items():
            app = Application(json.loads(app_config), name=name)
            app = yield app.load(need_details=False)

            result[name] = {}

            for service in app.services.values():
                if service.is_created():
                    result[name][service.shortname] = service.ip()

        defer.returnValue(result)

    @defer.inlineCallbacks
    def list(self, *args):

        deps = yield self.redis.hgetall('mcloud-deployments')

        # collect published applications
        pub_apps = {}
        for name, config_raw in deps.items():
            try:
                dep_dta = json.loads(config_raw)
                if 'exports' in dep_dta:
                    for dep in dep_dta['exports']:
                        if 'public_app' in dep and dep['public_app']:
                            if not dep['public_app'] in pub_apps:
                                pub_apps[dep['public_app']] = []

                            if not 'custom_port' in dep:
                                dep['custom_port'] = None

                            pub_apps[dep['public_app']].append({
                                'url': dep['name'],
                                'port': dep['custom_port'],
                                'service': dep['public_service'] if 'public_service' in dep else None
                            })

            except ValueError:
                pass

        # collect application data
        config = yield self.redis.hgetall('mcloud-apps')

        all_apps = []
        for name, app_config in config.items():
            try:
                public_urls = pub_apps[name]
            except KeyError:
                public_urls = None

            cfg = yield self.load_app_config(app_config)
            app = Application(cfg, name=name, public_urls=public_urls)
            all_apps.append(app.load(need_details=True))

        results = yield defer.gatherResults(all_apps, consumeErrors=True)

        defer.returnValue(results)


class ApplicationVolumeResolver(object):

    app_controller = inject.attr(ApplicationController)

    @inlineCallbacks
    def get_volume_path(self, app_name=None, service=None, volume=None):

        app = yield self.app_controller.get(app_name)

        if not service or not volume:
            defer.returnValue(app.config['path'])
        else:
            config = yield app.load()

            services = config.get_services()

            service = services['%s.%s' % (service, app_name)]

            all_volumes = service.list_volumes()
            if not volume in all_volumes:
                raise VolumeNotFound('Volume with name %s no found!' % volume)

            defer.returnValue(all_volumes[volume])