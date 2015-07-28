from glob import glob
import json
import os

import inject
from mcloud.events import EventBus
from mcloud.plugin import enumerate_plugins
from mcloud.txdocker import DockerTwistedClient
import pprintpp
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks
import txredisapi

from zope.interface import Interface


class IDeploymentPublishListener(Interface):

    def on_domain_publish(deployment, domain, ticket_id=None):
        """
        Called when domain is beeing published
        """

    def on_domain_unpublish(deployment, domain, ticket_id=None):
        """
        Called when domain is beeing published
        """



class Deployment(object):

    def __init__(self,
                 name=None,
                 exports=None,
                 host=None,
                 local=True,
                 port=None,
                 tls=False,
                 ca=None,
                 cert=None,
                 key=None,
                 default=None, **kwargs):
        super(Deployment, self).__init__()

        # "default" is ignored

        self.name = name
        self.exports = exports or {}
        self.host = host or 'unix://var/run/docker.sock/'
        self.port = port
        self.local = local
        self.tls = tls
        self.ca = ca
        self.cert = cert
        self.default = None
        self.key = key

        self.client = None

    def update(self, exports=None, host=None, local=None,  port=None, tls=False, ca=None, cert=None, key=None):
        if exports:
            self.exports = exports

        if host:
            self.host = host

        if local is not None:
            self.local = local

        if port is not None:
            self.port = port

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

        if self.local:
            url = self.host

        if '://' in self.host:
            scheme, host = self.host.split('://')
        else:
            scheme = 'tcp'
            host = self.host

        if ':' in host:
            host, port = host.split(':')
        else:
            port = self.port

        if scheme == 'tcp':
            scheme = 'https' if self.tls else 'http'
            port = self.port or '2375'
            url = '%s://%s:%s' % (scheme, host, port)

        self.client = DockerTwistedClient(url=url.encode(), key=self.key, crt=self.cert, ca=self.ca)
        return self.client


    @property
    def config(self):
        return {
            'name': self.name,
            'default': self.default,
            'exports': self.exports,
            'host': self.host,
            'port': self.port,
            'tls': self.tls,
            'local': self.local,
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
    def get_by_name_or_default(self, name=None):
        if name:
            deployment = yield self.get(name)
        else:
            deployment = yield self.get_default()

        # no deployments at all
        if not deployment:
            deployment = Deployment(name='local')

        defer.returnValue(deployment)

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
    def publish_app(self, deployment, domain, app_name, service_name, custom_port=None, ticket_id=None):
        if not isinstance(deployment, Deployment):
            deployment = yield self.get(deployment)

        deployment.exports[domain] = {
            'public_app': app_name,
            'public_service': service_name,
            'custom_port': custom_port
        }

        yield self._persist_dployment(deployment)

        for plugin in enumerate_plugins(IDeploymentPublishListener):
            yield plugin.on_domain_publish(deployment, domain, ticket_id=ticket_id)



    @inlineCallbacks
    def unpublish_app(self, deployment, domain, ticket_id=None):

        if not isinstance(deployment, Deployment):
            deployment = yield self.get(deployment)

        if domain in deployment.exports:
            del deployment.exports[domain]

        yield self._persist_dployment(deployment)

        for plugin in enumerate_plugins(IDeploymentPublishListener):
            yield plugin.on_domain_unpublish(deployment, domain, ticket_id=ticket_id)

    def _persist_dployment(self, deployment):
        return self.redis.hset('mcloud-deployments', deployment.name, json.dumps(deployment.config))



    @inlineCallbacks
    def configure_docker_machine(self):
        machine_path = '/.docker/machine'

        print 'Syncing deployments with Docker Machine'

        for path in glob('%s/machines/*' % machine_path):

            with open('%s/config.json' % path) as f:
                config = json.load(f)

                name = os.path.basename(path)
                host = config['Driver']['IPAddress']
                port = 3376
                tls = True

                files = {
                    'ca': None,
                    'cert': None,
                    'key': None,
                }
                for fname in files.keys():
                    with open('%s/%s.pem' % (path, fname)) as f:
                        files[fname] = f.read()

                try:
                    deployment = yield self.get(name)
                except DeploymentDoesNotExist:
                    deployment = None

                if deployment:
                    print 'Updating deployment %s' % name
                    yield self.update(
                        name=name,
                        host=host,
                        port=port,
                        tls=tls,
                        local=True,
                        **files
                    )
                else:
                    print 'Creating new deployment %s' % name
                    yield self.create(
                        name=name,
                        host=host,
                        port=port,
                        tls=tls,
                        local=True,
                        **files
                    )
                    # yield self.set_default(name)
                print '-' * 40

