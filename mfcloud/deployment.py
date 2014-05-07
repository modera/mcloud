import json
import inject
from mfcloud.application import ApplicationController, AppDoesNotExist
from mfcloud.config import ConfigParseError
from mfcloud.events import EventBus
from mfcloud.util import ValidationError
from twisted.internet import defer
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


    def load_data(self, *args, **kwargs):

        deployment = self.config

        apps = []
        for app in deployment['apps']:

            da = self.app_controller.get(app)
            def on_app_resolved(app_instance):

                def on_loaded(app_config):
                    services = []
                    for service in app_config.get_services().values():
                        services.append({
                            'name': service.name,
                            'running': service.is_running()
                        })

                    return {'name': app, 'config': app_instance.config, 'services': services}

                d = app_instance.load()
                d.addCallback(on_loaded)
                return d

            def on_error(failure):
                failure.trap(AppDoesNotExist, ConfigParseError)
                return None

            da.addCallback(on_app_resolved)
            da.addErrback(on_error)

            apps.append(da)

        print apps

        d = defer.gatherResults(apps, consumeErrors=True)

        def apps_received(app_data):
            deployment['apps'] = [app for app in app_data if not app is None]
            return deployment

        d.addCallback(apps_received)

        return d


class DeploymentDoesNotExist(Exception):
    pass


class DeploymentController(object):

    redis = inject.attr(txredisapi.Connection)
    app_controller = inject.attr(ApplicationController)
    eb = inject.attr(EventBus)

    """
    @type app_controller: ApplicationController
    """

    def create(self, name, domain):
        deployment = Deployment(name=name, public_domain=domain)
        d = self._persist_dployment(deployment)

        def on_ready(data):
            self.eb.fire_event('new-deployment', **data)
            return deployment

        d.addCallback(deployment.load_data)
        d.addCallback(on_ready)

        return d

    def remove(self, name):
        self.eb.fire_event('remove-deployment', name=name)
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
    def new_app(self, deployment_name, app_name, config):

        if app_name is None or str(app_name).strip() == '':
            raise ValidationError('App name shouldn\'t be empty')

        if deployment_name is None or str(deployment_name).strip() == '':
            raise ValidationError('Deployment name shouldn\'t be empty')

        deployment = yield self.get(deployment_name)
        app_full_name = '%s.%s' % (app_name, deployment_name)
        yield self.app_controller.create(app_full_name, config)
        deployment.apps.append(app_full_name)

        yield self._persist_dployment(deployment)

        data = yield deployment.load_data()

        self.eb.fire_event('updated-deployment', **data)

    def _persist_dployment(self, deployment):
        return self.redis.hset('mfcloud-deployments', deployment.name, json.dumps(deployment.config))

    @inlineCallbacks
    def remove_app(self, deployment_name, app_name):
        deployment = yield self.get(deployment_name)
        app_full_name = '%s.%s' % (app_name, deployment_name)
        deployment.apps.remove(app_full_name)

        yield self._persist_dployment(deployment)