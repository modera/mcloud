import json
import inject
from mcloud.application import ApplicationController, AppDoesNotExist
from mcloud.config import ConfigParseError
from mcloud.events import EventBus
from mcloud.util import ValidationError
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks
import txredisapi


class Deployment(object):

    app_controller = inject.attr(ApplicationController)

    def __init__(self, name=None, public_app=None, public_service=None, custom_port=None):
        super(Deployment, self).__init__()

        self.name = name
        self.public_app = public_app
        self.custom_port = None
        self.public_service = public_service

    @property
    def config(self):
        return {
            'name': self.name,
            'public_app': self.public_app,
            'custom_port': self.custom_port,
            'public_service': self.public_service,
        }

    def load_data(self, *args, **kwargs):
        return defer.succeed(self.config)


class DeploymentDoesNotExist(Exception):
    pass


class DeploymentController(object):

    redis = inject.attr(txredisapi.Connection)
    app_controller = inject.attr(ApplicationController)
    eb = inject.attr(EventBus)

    """
    @type app_controller: ApplicationController
    """


    @inlineCallbacks
    def create(self, name):
        deployment = Deployment(name=name)

        yield self._persist_dployment(deployment)
        data = yield deployment.load_data()

        self.eb.fire_event('new-deployment', **data)
        defer.returnValue(deployment)

    def remove(self, name):
        self.eb.fire_event('remove-deployment', name=name)
        return self.redis.hdel('mcloud-deployments', name)


    @inlineCallbacks
    def get(self, name):

        config = yield self.redis.hget('mcloud-deployments', name)

        if not config:
            raise DeploymentDoesNotExist('Deployment with name "%s" do not exist' % name)
        else:
            defer.returnValue(Deployment(**json.loads(config)))

    @inlineCallbacks
    def list(self):
        config = yield self.redis.hgetall('mcloud-deployments')
        defer.returnValue([Deployment(**json.loads(config)) for name, config in config.items()])

    @inlineCallbacks
    def publish_app(self, deployment_name, app_name, service_name, custom_port=None):
        try:
            deployment = yield self.get(deployment_name)
        except DeploymentDoesNotExist:
            deployment = yield self.create(deployment_name)

        deployment.public_app = app_name
        deployment.custom_port = custom_port
        deployment.public_service = service_name

        yield self._persist_dployment(deployment)

        app_data = yield self.app_controller.list()
        self.eb.fire_event('containers.updated', apps=app_data)


    @inlineCallbacks
    def unpublish_app(self, deployment_name):
        yield self.remove(deployment_name)

        app_data = yield self.app_controller.list()
        self.eb.fire_event('containers.updated', apps=app_data)

    def _persist_dployment(self, deployment):
        return self.redis.hset('mcloud-deployments', deployment.name, json.dumps(deployment.config))
