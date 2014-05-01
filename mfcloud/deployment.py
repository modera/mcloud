import json
import logging
import inject
from mfcloud.application import ApplicationController
from mfcloud.config import YamlConfig, ConfigParseError
import os
from twisted.internet import defer, reactor
from twisted.internet.defer import inlineCallbacks
import txredisapi


class Deployment(object):

    app_controller = inject.attr(ApplicationController)

    def __init__(self, public_domain=None, name=None, apps=None):
        super(Deployment, self).__init__()

        self.public_domain = public_domain
        self.name = name
        self.apps = apps

    @property
    def config(self):
        return {
            'name': self.name,
            'public_domain': self.public_domain,
            'apps': self.apps or []
        }


class DeploymentDoesNotExist(Exception):
    pass


class DeploymentController(object):

    redis = inject.attr(txredisapi.Connection)
    app_controller = inject.attr(ApplicationController)
    """
    @type app_controller: ApplicationController
    """

    def create(self, name, domain):
        deployment = Deployment(name=name, public_domain=domain)
        d = self._persist_dployment(deployment)
        d.addCallback(lambda r: deployment)

        return d

    def remove(self, name):
        return self.redis.hdel('mfcloud-deployments', name)

    def get(self, name):

        d = self.redis.hget('mfcloud-deployments', name)

        def ready(config):
            if not config:
                raise DeploymentDoesNotExist('Deployment with name "%s" do not exist' % name)
            else:
                return Deployment(**json.loads(config))

        d.addCallback(ready)

        return d

    def list(self):
        d = self.redis.hgetall('mfcloud-deployments')

        def ready(config):
            return [Deployment(**json.loads(config)) for name, config in config.items()]
        d.addCallback(ready)

        return d

    @inlineCallbacks
    def new_app(self, deployment_name, app_name, app_path):
        deployment = yield self.get(deployment_name)
        app_full_name = '%s.%s' % (app_name, deployment_name)
        yield self.app_controller.create(app_full_name, app_path)
        deployment.apps.append(app_full_name)

        yield self._persist_dployment(deployment)

    def _persist_dployment(self, deployment):
        return self.redis.hset('mfcloud-deployments', deployment.name, json.dumps(deployment.config))

    @inlineCallbacks
    def remove_app(self, deployment_name, app_name):
        deployment = yield self.get(deployment_name)
        app_full_name = '%s.%s' % (app_name, deployment_name)
        deployment.apps.remove(app_full_name)

        yield self._persist_dployment(deployment)