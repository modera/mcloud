import inspect
import logging
import inject
from mfcloud.application import ApplicationController, Application, AppDoesNotExist
from mfcloud.config import ConfigParseError
from mfcloud.deployment import DeploymentController
from twisted.internet import defer, reactor
from twisted.internet.defer import Deferred, DeferredList, inlineCallbacks


logger = logging.getLogger('mfcloud.tasks')

class TaskService():
    app_controller = inject.attr(ApplicationController)
    deployment_controller = inject.attr(DeploymentController)

    """
    @type app_controller: ApplicationController
    """

    def task_help(self, ticket_id):
        pass

    def task_init(self, ticket_id, name, path):

        d = self.app_controller.create(name, {'path': path})

        def done(app):
            return not app is None

        d.addCallback(done)
        return d

    def task_init_source(self, ticket_id, name, source):

        d = self.app_controller.create(name, {'source': source})

        def done(app):
            return not app is None

        d.addCallback(done)
        return d

    def task_list(self, ticket_id):
        d = self.app_controller.list()

        def done(apps):
            all = []
            for name, app in apps.items():
                if 'path' in app.config:
                    path = app.config['path']
                else:
                    path = None
                all.append((name, path))
            return all

        d.addCallback(done)
        return d

    def task_remove(self, ticket_id, name):
        d = self.app_controller.remove(name)

        # d.addCallback(done)
        return d

    def task_status(self, ticket_id, name):
        d = self.app_controller.get(name)

        def on_result(config):
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

            return data

        d.addCallback(lambda app: app.load())
        d.addCallback(on_result)
        return d

    def task_start(self, ticket_id, name):

        logger.debug('[%s] Starting application' % (ticket_id, ))

        d = self.app_controller.get(name)

        def on_result(config):
            """
            @type config: YamlConfig
            """

            logger.debug('[%s] Got response' % (ticket_id, ))

            d = []
            for service in config.get_services().values():
                if not service.is_running():
                    logger.debug('[%s] Service %s is not running. Starting' % (ticket_id, service.name))
                    d.append(service.start(ticket_id))
                else:
                    logger.debug('[%s] Service %s is already running.' % (ticket_id, service.name))

            return DeferredList(d)

        d.addCallback(lambda app: app.load())
        d.addCallback(on_result)
        return d

    def task_stop(self, ticket_id, name):

        logger.debug('[%s] Stoping application' % (ticket_id, ))

        d = self.app_controller.get(name)

        def on_result(config):
            """
            @type config: YamlConfig
            """

            logger.debug('[%s] Got response' % (ticket_id, ))

            d = []
            for service in config.get_services().values():
                if service.is_running():
                    logger.debug('[%s] Service %s is running. Stoping' % (ticket_id, service.name))
                    d.append(service.stop(ticket_id))
                else:
                    logger.debug('[%s] Service %s is already stopped.' % (ticket_id, service.name))

            return DeferredList(d)

        d.addCallback(lambda app: app.load())
        d.addCallback(on_result)
        return d

    def task_inspect(self, ticket_id, name, service_name):

        logger.debug('[%s] Inspecting application service %s' % (ticket_id, service_name))

        d = self.app_controller.get(name)

        def on_result(config):
            """
            @type config: YamlConfig
            """
            logger.debug('[%s] Got response' % (ticket_id, ))

            service = config.get_service(service_name)
            if not service.is_running():
                return 'Not running'
            else:
                if not service.is_inspected():
                    return service.inspect()
                else:
                    return service._inspect_data


        d.addCallback(lambda app: app.load())
        d.addCallback(on_result)
        return d

    def task_deployments(self, ticket_id):
        d = self.deployment_controller.list()

        def done(deployments):
            deployment_list = []

            for deployment in deployments:
                deployment_list.append(deployment.load_data())

            return defer.gatherResults(deployment_list, consumeErrors=True)

        d.addCallback(done)
        return d


    def task_deployment_details(self, ticket_id, name):
        d = self.deployment_controller.get(name)

        def done(deployment):
            return deployment.load_data()

        d.addCallback(done)
        return d

    def task_deployment_create(self, ticket_id, name, public_domain):

        d = self.deployment_controller.create(name, public_domain)

        def done(deployment):
            return not deployment is None

        d.addCallback(done)
        return d

    def task_deployment_new_app_source(self, ticket_id, deployment_name, name, source):

        d = self.deployment_controller.new_app(deployment_name, name, {'source': source})

        def done(app):
            return not app is None

        d.addCallback(done)
        return d

    def task_deployment_remove(self, ticket_id, name):

        d = self.deployment_controller.remove(name)

        def done(deployment):
            return not deployment is None

        d.addCallback(done)
        return d

    #
    #def task_deployment_details(self, ticket_id, name):
    #    d = self.deployment_controller.get(name)
    #
    #    def done(deployment):
    #        deployment_list = []
    #
    #        for deployment in deployments:
    #            print deployment
    #            data = deployment.config
    #            deployment_list.append(self.expand_app_list_on_deployment(data))
    #
    #        return defer.gatherResults(deployment_list, consumeErrors=True)
    #
    #    d.addCallback(done)
    #    return d

    def register(self, rpc_server):

        tasks = {}

        for name, func in inspect.getmembers(self):
            if name.startswith('task_'):
                tasks[name[5:]] = func

        rpc_server.tasks.update(tasks)