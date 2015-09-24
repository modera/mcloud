from glob import glob
import json

from mcloud.app.models import Deployment
import os
import inject
from mcloud.events import EventBus
from mcloud.plugin import enumerate_plugins
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
        try:
            deployment = yield Deployment.tx.get(name=name)
            defer.returnValue(deployment)

        except Deployment.DoesNotExist:
            raise DeploymentDoesNotExist('Deployment with name "%s" do not exist' % name)


    @inlineCallbacks
    def get_default(self):
        deployments = yield Deployment.tx.filter(default=True)
        if deployments.conunt() > 0:
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
        deployments = yield Deployment.tx.all()
        defer.returnValue(deployments)

    @inlineCallbacks
    def set_default(self, name):
        deployment = yield self.get(name)

        # reset default
        yield Deployment.tx.update(default=False)

        # set default
        deployment.default = True
        yield deployment.save()

    @inlineCallbacks
    def publish_app(self, deployment, domain, app_name, service_name, custom_port=None, ticket_id=None):


        if not isinstance(deployment, Deployment):
            deployment = yield self.get(deployment)

        # deployment.exports[domain] = {
        #     'public_app': app_name,
        #     'public_service': service_name,
        #     'custom_port': custom_port
        # }

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
        return deployment.save()



    @inlineCallbacks
    def configure_docker_machine(self):
        machine_path = '/.docker/machine'

        print 'Syncing deployments with Docker Machine'

        for path in glob('%s/machines/*' % machine_path):

            with open('%s/config.json' % path) as f:
                config = json.load(f)

                name = os.path.basename(path)
                host = config['Driver']['IPAddress']
                port = 2376
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
                        local=False,
                        **files
                    )
                else:
                    print 'Creating new deployment %s' % name
                    yield self.create(
                        name=name,
                        host=host,
                        port=port,
                        tls=tls,
                        local=False,
                        **files
                    )
                    # yield self.set_default(name)
                print '-' * 40

