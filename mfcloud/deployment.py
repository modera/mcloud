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

    def __init__(self, public_domain=None, name=None, apps=None, public_app=None):
        super(Deployment, self).__init__()

        self.public_domain = public_domain
        self.public_app = public_app
        self.name = name
        self.apps = apps

    @property
    def config(self):
        return {
            'name': self.name,
            'public_domain': self.public_domain,
            'public_app': self.public_app,
            'apps': self.apps or []
        }


    @inlineCallbacks
    def load_data(self, *args, **kwargs):

        deployment = self.config

        apps = []
        for app in deployment['apps']:

            da = self.app_controller.get(app)
            def on_app_resolved(app_instance):
                return app_instance.load(need_details=True)

            def on_error(failure):
                failure.trap(AppDoesNotExist, ConfigParseError)
                return None

            da.addCallback(on_app_resolved)
            da.addErrback(on_error)

            apps.append(da)

        app_data = yield defer.gatherResults(apps, consumeErrors=True)

        deployment['apps'] = [app for app in app_data if not app is None]
        defer.returnValue(deployment)


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
    def create(self, name, domain):
        deployment = Deployment(name=name, public_domain=domain)

        yield self._persist_dployment(deployment)
        data = yield deployment.load_data()

        self.eb.fire_event('new-deployment', **data)
        defer.returnValue(deployment)

    def remove(self, name):
        self.eb.fire_event('remove-deployment', name=name)
        return self.redis.hdel('mfcloud-deployments', name)


    @inlineCallbacks
    def get(self, name):

        config = yield self.redis.hget('mfcloud-deployments', name)

        if not config:
            raise DeploymentDoesNotExist('Deployment with name "%s" do not exist' % name)
        else:
            defer.returnValue(Deployment(**json.loads(config)))

    @inlineCallbacks
    def list(self):
        config = yield self.redis.hgetall('mfcloud-deployments')
        defer.returnValue([Deployment(**json.loads(config)) for name, config in config.items()])

    @inlineCallbacks
    def publish_app(self, deployment_name, app_name):
        deployment = yield self.get(deployment_name)

        app_full_name = '%s.%s' % (app_name, deployment_name)

        deployment.public_app = app_full_name

        yield self._persist_dployment(deployment)

        app_data = yield self.app_controller.list()
        self.eb.fire_event('containers-updated', apps=app_data)



    @inlineCallbacks
    def unpublish_app(self, deployment_name):
        deployment = yield self.get(deployment_name)
        deployment.public_app = None

        yield self._persist_dployment(deployment)

        app_data = yield self.app_controller.list()
        self.eb.fire_event('containers-updated', apps=app_data)


    @inlineCallbacks
    def new_app(self, deployment_name, app_name, config, skip_validation=False, skip_events=False):

        if app_name is None or str(app_name).strip() == '':
            raise ValidationError('App name shouldn\'t be empty')

        if deployment_name is None or str(deployment_name).strip() == '':
            raise ValidationError('Deployment name shouldn\'t be empty')

        deployment = yield self.get(deployment_name)
        app_full_name = '%s.%s' % (app_name, deployment_name)
        yield self.app_controller.create(app_full_name, config, skip_validation=skip_validation)
        deployment.apps.append(app_full_name)

        yield self._persist_dployment(deployment)

        if not skip_events:
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