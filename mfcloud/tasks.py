import inspect
import logging
from autobahn.twisted import wamp
from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import ApplicationSession
import inject
from mfcloud.application import ApplicationController, Application, AppDoesNotExist
from mfcloud.config import ConfigParseError
from mfcloud.deployment import DeploymentController
from mfcloud.events import EventBus
from mfcloud.remote import ApiRpcServer
from twisted.internet import defer, reactor
from twisted.internet.defer import Deferred, DeferredList, inlineCallbacks
import txredisapi

from twisted.python import log


class TaskService(object):
    """
    @type app_controller: ApplicationController
    """
    app_controller = inject.attr(ApplicationController)
    deployment_controller = inject.attr(DeploymentController)
    redis = inject.attr(txredisapi.Connection)
    rpc_server = inject.attr(ApiRpcServer)
    event_bus = inject.attr(EventBus)

    dns_server = inject.attr('dns-server')
    dns_search_suffix = inject.attr('dns-search-suffix')

    def task_log(self, ticket_id, message):
        self.rpc_server.task_progress(message, ticket_id)

    def task_help(self, ticket_id):
        pass

    @inlineCallbacks
    def task_init(self, ticket_id, name, path):

        yield self.app_controller.create(name, {'path': path})

        ret = yield self.app_controller.list()
        defer.returnValue(ret)

    @inlineCallbacks
    def task_init_source(self, ticket_id, name, source):

        yield self.app_controller.create(name, {'source': source})

        ret = yield self.app_controller.list()
        defer.returnValue(ret)

    @inlineCallbacks
    def task_list(self, ticket_id):
        alist = yield self.app_controller.list()
        defer.returnValue(alist)

    @inlineCallbacks
    def task_list_vars(self, ticket_id):
        vlist = yield self.redis.hgetall('vars')
        defer.returnValue(vlist)

    @inlineCallbacks
    def task_set_var(self, ticket_id, name, val):
        yield self.redis.hset('vars', name, val)
        defer.returnValue((yield self.task_list_vars(ticket_id)))

    @inlineCallbacks
    def task_rm_var(self, ticket_id, name):
        yield self.redis.hdel('vars', name)
        defer.returnValue((yield self.task_list_vars(ticket_id)))

    @inlineCallbacks
    def task_remove(self, ticket_id, name):
        yield self.task_destroy(ticket_id, name)
        yield self.app_controller.remove(name)

        ret = yield self.app_controller.list()
        defer.returnValue(ret)


    @inlineCallbacks
    def task_status(self, ticket_id, name):
        app = yield self.app_controller.get(name)
        config = yield app.load()

        """
        @type config: YamlConfig
        """

        data = []
        for service in config.get_services().values():
            """
            @type service: Service
            """

            assert service.is_inspected()

            data.append([
                service.name,
                service.is_running(),
                service.is_running()
            ])

        defer.returnValue(data)

    def sleep(self, sec):
        d = defer.Deferred()
        reactor.callLater(sec, d.callback, None)
        return d


    @inlineCallbacks
    def task_dns(self, ticket_id):
        data = yield self.redis.hgetall('domain')

        defer.returnValue(data)

    @inlineCallbacks
    def task_restart(self, ticket_id, name):
        yield self.task_stop(ticket_id, name)
        ret = yield self.task_start(ticket_id, name)

        defer.returnValue(ret)

    @inlineCallbacks
    def task_rebuild(self, ticket_id, name):
        yield self.task_destroy(ticket_id, name)
        ret = yield self.task_start(ticket_id, name)

        defer.returnValue(ret)


    @inlineCallbacks
    def task_start(self, ticket_id, name):

        self.task_log(ticket_id, '[%s] Starting application' % (ticket_id, ))

        if '.' in name:
            service_name, app_name = name.split('.')
        else:
            service_name = None
            app_name = name

        app = yield self.app_controller.get(app_name)
        config = yield app.load()

        """
        @type config: YamlConfig
        """

        self.task_log(ticket_id, '[%s] Got response' % (ticket_id, ))

        for service in config.get_services().values():
            if service_name and '%s.%s' % (service_name, app_name) != service.name:
                continue

            if not service.is_created():
                self.task_log(ticket_id,
                              '[%s] Service %s is not created. Creating' % (ticket_id, service.name))
                yield service.create(ticket_id)

        for service in config.get_services().values():
            if service_name and '%s.%s' % (service_name, app_name) != service.name:
                continue

            if not service.is_running():
                self.task_log(ticket_id,
                              '[%s] Service %s is not running. Starting' % (ticket_id, service.name))
                yield service.start(ticket_id)

                self.task_log(ticket_id, 'Updating container list')
                self.event_bus.fire_event('containers-updated')

                yield sleep(0.2)
            else:
                self.task_log(ticket_id,
                              '[%s] Service %s is already running.' % (ticket_id, service.name))

        ret = yield self.app_controller.list()
        defer.returnValue(ret)


    @inlineCallbacks
    def task_create(self, ticket_id, name):

        self.task_log(ticket_id, '[%s] Creating application' % (ticket_id, ))

        if '.' in name:
            service_name, app_name = name.split('.')
        else:
            service_name = None
            app_name = name

        app = yield self.app_controller.get(app_name)
        config = yield app.load()

        """
        @type config: YamlConfig
        """

        self.task_log(ticket_id, '[%s] Got response' % (ticket_id, ))

        for service in config.get_services().values():
            if service_name and '%s.%s' % (service_name, app_name) != service.name:
                continue

            if not service.is_created():
                self.task_log(ticket_id,
                              '[%s] Service %s is not created. Creating' % (ticket_id, service.name))
                yield service.create(ticket_id)

        ret = yield self.app_controller.list()
        defer.returnValue(ret)


    @inlineCallbacks
    def task_push(self, ticket_id, app_name, service_name, volume):

        app = yield self.app_controller.get(app_name)
        config = yield app.load()

        name = '_volumes_%s.%s' % (service_name, app_name)

        service = config.get_services()[name]

        """
        @type service: mfcloud.service.Service
        """
        port = service.public_ports()['22/tcp'][0]['HostPort']

        defer.returnValue(port)

    @inlineCallbacks
    def task_run(self, ticket_id, app_name, service_name):

        app = yield self.app_controller.get(app_name)
        config = yield app.load()

        service_name = '%s.%s' % (service_name, app_name)

        service = config.get_services()[service_name]

        defer.returnValue({
            'image': service.image(),
            'hosts_path': service.hosts_path(),
            'dns-server': self.dns_server,
            'dns-suffix': self.dns_search_suffix,
        })

    @inlineCallbacks
    def task_stop(self, ticket_id, name):

        self.task_log(ticket_id, '[%s] Stoping application' % (ticket_id, ))

        if '.' in name:
            service_name, app_name = name.split('.')
        else:
            service_name = None
            app_name = name

        app = yield self.app_controller.get(app_name)
        config = yield app.load()

        """
        @type config: YamlConfig
        """

        self.task_log(ticket_id, '[%s] Got response' % (ticket_id, ))

        d = []
        for service in config.get_services().values():

            if service_name and '%s.%s' % (service_name, app_name) != service.name:
                continue

            if service.is_running():
                self.task_log(ticket_id,
                              '[%s] Service %s is running. Stoping' % (ticket_id, service.name))
                d.append(service.stop(ticket_id))
            else:
                self.task_log(ticket_id,
                              '[%s] Service %s is already stopped.' % (ticket_id, service.name))

        yield defer.gatherResults(d)

        ret = yield self.app_controller.list()
        defer.returnValue(ret)

    @inlineCallbacks
    def task_destroy(self, ticket_id, name):

        self.task_log(ticket_id, '[%s] Destroying application containers' % (ticket_id, ))

        if '.' in name:
            service_name, app_name = name.split('.')
        else:
            service_name = None
            app_name = name

        app = yield self.app_controller.get(app_name)
        config = yield app.load()

        """
        @type config: YamlConfig
        """

        self.task_log(ticket_id, '[%s] Got response' % (ticket_id, ))

        if isinstance(config, dict):
            self.task_log(ticket_id, 'Application location does not exist, use remove command to remove application')
            self.task_log(ticket_id, config['message'])
            return

        d = []
        for service in config.get_services().values():

            if service_name and '%s.%s' % (service_name, app_name) != service.name:
                continue

            self.task_log(ticket_id, '[%s] Destroying container: %s' % (ticket_id, service_name))

            if service.is_created():
                if service.is_running():
                    self.task_log(ticket_id,
                                  '[%s] Service %s container is running. Stopping and then destroying' % (
                                      ticket_id, service.name))
                    yield service.stop(ticket_id)
                    d.append(service.destroy(ticket_id))

                else:
                    self.task_log(ticket_id,
                                  '[%s] Service %s container is created. Destroying' % (ticket_id, service.name))
                    d.append(service.destroy(ticket_id))
            else:
                self.task_log(ticket_id,
                              '[%s] Service %s container is not yet created.' % (ticket_id, service.name))

        yield defer.gatherResults(d)

        ret = yield self.app_controller.list()
        defer.returnValue(ret)


    @inlineCallbacks
    def task_inspect(self, ticket_id, name, service_name):

        self.task_log(ticket_id, '[%s] Inspecting application service %s' %
                                 (ticket_id, service_name))

        app = yield self.app_controller.get(name)
        config = yield app.load()

        """
        @type config: YamlConfig
        """
        self.task_log(ticket_id, '[%s] Got response' % (ticket_id, ))

        service = config.get_service(service_name)
        if not service.is_running():
            defer.returnValue('Not running')
        else:
            if not service.is_inspected():
                ret = yield service.inspect()
                defer.returnValue(ret)
            else:
                defer.returnValue(service._inspect_data)


    @inlineCallbacks
    def task_deployments(self, ticket_id):
        deployments = yield self.deployment_controller.list()

        deployment_list = []

        for deployment in deployments:
            deployment_list.append(deployment.load_data())

        ret = yield defer.gatherResults(deployment_list, consumeErrors=True)
        defer.returnValue(ret)

    #
    # @inlineCallbacks
    # def task_deployment_create(self, ticket_id, public_domain):
    #     deployment = yield self.deployment_controller.create(public_domain)
    #     defer.returnValue(not deployment is None)
    #
    # @inlineCallbacks
    # def task_deployment_new_app_zip(self, ticket_id, deployment_name, name, path):
    #     app = yield self.deployment_controller.new_app(deployment_name, name, {'path': path})
    #     defer.returnValue(not app is None)
    #
    # @inlineCallbacks
    # def task_deployment_new_app_source(self, ticket_id, deployment_name, name, source):
    #     app = yield self.deployment_controller.new_app(deployment_name, name, {'source': source})
    #     defer.returnValue(not app is None)

    @inlineCallbacks
    def task_publish(self, ticket_id, deployment_name, app_name):
        yield self.deployment_controller.publish_app(deployment_name, app_name)

        ret = yield self.app_controller.list()
        defer.returnValue(ret)

    @inlineCallbacks
    def task_unpublish(self, ticket_id, deployment_name):
        yield self.deployment_controller.unpublish_app(deployment_name)

        ret = yield self.app_controller.list()
        defer.returnValue(ret)

    def collect_tasks(self, ):

        tasks = {}
        for name, func in inspect.getmembers(self):
            if name.startswith('task_'):
                tasks[name[5:]] = func

        return tasks

