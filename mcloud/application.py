import json
from mcloud.app.models import Application

from mcloud.deployment import DeploymentController, DeploymentDoesNotExist
import re
import inject
from mcloud.config import YamlConfig
import os
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks
import txredisapi



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
    def create(self, name, config, skip_validation=False):

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
        Application.objects.filter(name=name).delete()
        defer.returnValue(True)

    @defer.inlineCallbacks
    def load_app_config(self, config):
        cfg = json.loads(config)
        if not 'deployment' in cfg:
            cfg['deployment'] = yield self.redis.get('mcloud-deployment-default')

        defer.returnValue(cfg)

    @defer.inlineCallbacks
    def get(self, name):

        try:
            app = yield Application.tx.get(name=name)
            defer.returnValue(app)

        except Application.AppDoesNotExist:
            raise AppDoesNotExist('Application with name "%s" do not exist' % name)


    @defer.inlineCallbacks
    def volume_list(self, *args):


        apps = yield self.list()

        result = {}

        for app in apps:
            result[app.name] = {}

            for service in app.services:
                result[service.name] = service.volumes

        defer.returnValue(result)

    @defer.inlineCallbacks
    def ip_list(self, *args):

        apps = yield self.list(need_details=False)

        result = {}

        for app in apps:
            result[app.name] = {}

            for service in list(app.services.values()):
                if service.is_created():
                    result[app.name][service.shortname] = service.ip()

        defer.returnValue(result)

    @defer.inlineCallbacks
    def list(self, need_details=True, *args):

        # deps = yield self.redis.hgetall('mcloud-deployments')
        #
        # # collect published applications
        # pub_apps = {}
        # for name, config_raw in deps.items():
        #     try:
        #         dep_dta = json.loads(config_raw)
        #
        #         if 'exports' in dep_dta:
        #             for domain_name, dep in dep_dta['exports'].items():
        #
        #                 if 'public_app' in dep and dep['public_app']:
        #                     if not dep['public_app'] in pub_apps:
        #                         pub_apps[dep['public_app']] = []
        #
        #                     if not 'custom_port' in dep:
        #                         dep['custom_port'] = None
        #
        #                     pub_apps[dep['public_app']].append({
        #                         'url': domain_name,
        #                         'port': dep['custom_port'],
        #                         'service': dep['public_service'] if 'public_service' in dep else None
        #                     })
        #
        #     except ValueError:
        #         pass

        # collect application data
        apps = yield Application.tx.all()

        all_apps = []
        for app in apps:
            all_apps.append(app.load(need_details=need_details))

        results = yield defer.gatherResults(all_apps, consumeErrors=True)

        defer.returnValue(results)
