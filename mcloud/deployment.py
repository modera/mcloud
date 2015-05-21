import json

import inject
from mcloud.events import EventBus
from mcloud.txdocker import DockerTwistedClient
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks
import txredisapi


class Deployment(object):

    def __init__(self, name=None, exports=None, host=None, tls=False, ca=None, cert=None, key=None, default=None):
        super(Deployment, self).__init__()

        # "default" is ignored

        self.name = name
        self.exports = exports or {}
        self.host = host or 'unix://var/run/docker.sock/'
        self.tls = tls
        self.ca = ca
        self.cert = cert
        self.default = None
        self.key = key

        self.client = None

    def update(self, exports=None, host=None, tls=False, ca=None, cert=None, key=None):
        if exports:
            self.exports = exports

        if host:
            self.host = host or 'unix://var/run/docker.sock/'

        if tls is not None:
            self.tls = tls

        if ca is not None:
            self.ca = ca or None

        if cert is not None:
            self.cert = cert or None

        if key is not None:
            self.key = key or None


    def get_client(self):
        if self.client:
            return self.client

        self.client = DockerTwistedClient(url=self.host.encode())
        return self.client


    @property
    def config(self):
        return {
            'name': self.name,
            'default': self.default,
            'exports': self.exports,
            'host': self.host,
            'tls': self.tls,
            'ca': self.ca,
            'key': self.key,
            'cert': self.cert
        }

    def load_data(self, *args, **kwargs):
        return defer.succeed(self.config)


class DeploymentDoesNotExist(Exception):
    pass


class DeploymentController(object):

    redis = inject.attr(txredisapi.Connection)
    eb = inject.attr(EventBus)

    """
    @type app_controller: ApplicationController
    """


    @inlineCallbacks
    def create(self, name, **kwargs):
        deployment = Deployment(name=name, **kwargs)

        yield self._persist_dployment(deployment)
        data = yield deployment.load_data()

        self.eb.fire_event('new-deployment', **data)
        defer.returnValue(deployment)

    @inlineCallbacks
    def set_default(self, name):
        yield self.redis.set('mcloud-deployment-default', name)

    @inlineCallbacks
    def update(self, name, **kwargs):
        deployment = yield self.get(name)

        deployment.update(**kwargs)

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
    def get_default(self):
        config = yield self.redis.hgetall('mcloud-deployments')
        default = yield self.redis.get('mcloud-deployment-default')

        deployments = [Deployment(**json.loads(config)) for name, config in config.items()]

        for dpl in deployments:
            if dpl.name == default:
                defer.returnValue(dpl)

        if len(deployments) > 0:
            defer.returnValue(deployments[0])

        defer.returnValue(None)

    @inlineCallbacks
    def list(self):
        config = yield self.redis.hgetall('mcloud-deployments')
        default = yield self.redis.get('mcloud-deployment-default')

        deployments = [Deployment(**json.loads(config)) for name, config in config.items()]

        for dpl in deployments:
            dpl.default = dpl.name == default

        defer.returnValue(deployments)

    @inlineCallbacks
    def set_default(self, name):
        yield self.redis.set('mcloud-deployment-default', name)

    @inlineCallbacks
    def publish_app(self, name, domain, app_name, service_name, custom_port=None):
        deployment = yield self.get(name)

        deployment.exports[domain] = {
            'public_app': app_name,
            'public_service': service_name,
            'custom_port': custom_port
        }

        yield self._persist_dployment(deployment)


    @inlineCallbacks
    def unpublish_app(self, name, domain):
        deployment = yield self.get(name)

        if domain in deployment.exports:
            del deployment.exports[domain]

        yield self._persist_dployment(deployment)

    def _persist_dployment(self, deployment):
        return self.redis.hset('mcloud-deployments', deployment.name, json.dumps(deployment.config))
