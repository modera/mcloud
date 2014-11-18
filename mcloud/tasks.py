import inspect
import random
import string
from mcloud.container import PrebuiltImageBuilder
from mcloud.service import Service
from mcloud.sync import VolumeNotFound
import os

import re
from autobahn.twisted.util import sleep
import inject
from twisted.internet import defer, reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.error import ConnectionDone
import txredisapi
from mcloud.txdocker import IDockerClient, NotFound
from mcloud.application import ApplicationController, AppDoesNotExist
from mcloud.deployment import DeploymentController
from mcloud.events import EventBus
from mcloud.remote import ApiRpcServer


class TaskService(object):

    app_controller = inject.attr(ApplicationController)
    """
    @type app_controller: ApplicationController
    """
    deployment_controller = inject.attr(DeploymentController)
    redis = inject.attr(txredisapi.Connection)
    rpc_server = inject.attr(ApiRpcServer)
    event_bus = inject.attr(EventBus)
    """ @type: EventBus """

    dns_server = inject.attr('dns-server')
    dns_search_suffix = inject.attr('dns-search-suffix')

    def task_log(self, ticket_id, message):

        self.rpc_server.task_progress(message, ticket_id)

    def task_help(self, ticket_id):
        pass

    @inlineCallbacks
    def task_init(self, ticket_id, name, path=None, config=None, env=None):
        """
        Initialize new application

        :param ticket_id:
        :param name: Application name
        :param path: Path to the application
        :return:
        """

        app = None
        try:
            app = yield self.app_controller.get(name)
        except AppDoesNotExist:
            pass

        if app:
            raise ValueError('Application already exist')

        if not config:
            raise ValueError('config must be provided to create an application')

        if not path:
            home_dir = os.path.expanduser('~/.mcloud')
            path = os.path.join(home_dir, name)
            if not os.path.exists(path):
                os.makedirs(path, 0700)

        yield self.app_controller.create(name, {'path': path, 'source': config, 'env': env})

        defer.returnValue(True)

    @inlineCallbacks
    def task_update(self, ticket_id, name, config=None, env=None):
        """
        Initialize new application

        :param ticket_id:
        :param name: Application name
        :param path: Path to the application
        :return:
        """

        yield self.app_controller.update_source(name, source=config, env=env)

        ret = yield self.app_controller.list()
        defer.returnValue(ret)

    @inlineCallbacks
    def task_list(self, ticket_id):
        """
        List all application and data related

        :param ticket_id:
        :return:
        """
        alist = yield self.app_controller.list()
        defer.returnValue(alist)

    @inlineCallbacks
    def task_list_volumes(self, ticket_id):
        """
        List all volumes of all applications

        :param ticket_id:
        :return:
        """
        alist = yield self.app_controller.volume_list()
        defer.returnValue(alist)

    @inlineCallbacks
    def task_list_vars(self, ticket_id):
        """
        List variables

        :param ticket_id:
        :return:
        """
        vlist = yield self.redis.hgetall('vars')
        defer.returnValue(vlist)

    @inlineCallbacks
    def task_set_var(self, ticket_id, name, val):
        """
        Set variable

        :param ticket_id:
        :param name:
        :param val:
        :return:
        """
        yield self.redis.hset('vars', name, val)
        defer.returnValue((yield self.task_list_vars(ticket_id)))

    @inlineCallbacks
    def task_rm_var(self, ticket_id, name):
        """
        Remove variable

        :param ticket_id:
        :param name:
        :return:
        """
        yield self.redis.hdel('vars', name)
        defer.returnValue((yield self.task_list_vars(ticket_id)))

    @inlineCallbacks
    def task_remove(self, ticket_id, name):
        """
        Remove application

        :param ticket_id:
        :param name:
        :return:
        """
        yield self.task_destroy(ticket_id, name)
        yield self.app_controller.remove(name)

        # ret = yield self.app_controller.list()
        ret = 'Done.'
        defer.returnValue(ret)


    @inlineCallbacks
    def task_logs(self, ticket_id, name):
        """
        Read logs.

        Logs are streamed as task output.

        :param ticket_id:
        :param name:
        :return:
        """

        def on_log(log):
            log = log[8:]
            self.task_log(ticket_id, log)

        try:
            client = inject.instance(IDockerClient)
            yield client.logs(name, on_log, tail=100)
        except NotFound:
            self.task_log(ticket_id, 'Container not found by name.')


    @inlineCallbacks
    def task_attach(self, ticket_id, container_id, size=None):
        """
        Attach to container.

        TaskIO is attached to container.

        :param ticket_id:
        :param container_id:
        :param size:
        :return:
        """
        try:
            client = inject.instance(IDockerClient)
            yield client.attach(container_id, ticket_id)
        except NotFound:
            self.task_log(ticket_id, 'Container not found by name.')


    @inlineCallbacks
    def task_run(self, ticket_id, name, command, size=None):
        """
        Run command in container.

        TaskIO is attached to container.

        :param ticket_id:
        :param name:
        :param command:
        :param size:
        :return:
        """

        service_name, app_name = name.split('.')

        try:
            app = yield self.app_controller.get(app_name)

            config = yield app.load()

            services = config.get_services()

            service = services['%s.%s' % (service_name, app_name)]

            yield service.run(ticket_id, command, size=size)

        except NotFound:
            self.task_log(ticket_id, 'Container not found by name.')

        except ConnectionDone:
            pass


    @inlineCallbacks
    def task_config(self, ticket_id, name):
        """
        Show application detailed status

        :param ticket_id:
        :param name:
        :return:
        """
        app = yield self.app_controller.get(name)
        config = yield app.load()

        defer.returnValue({
            'path': app.config['path'],
            'env': app.get_env(),
            'source': app.config['source'],
            'hosts': config.get_hosts(),
            'volumes': config.get_volumes(),
        })


    @inlineCallbacks
    def task_status(self, ticket_id, name):
        """
        Show application detailed status

        :param ticket_id:
        :param name:
        :return:
        """
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
        """
        Show dns allocation table.

        :param ticket_id:
        :return:
        """
        data = yield self.redis.hgetall('domain')

        defer.returnValue(data)

    @inlineCallbacks
    def task_restart(self, ticket_id, name):
        """
        Restart application or services

        :param ticket_id:
        :param name:
        :return:
        """

        yield self.task_stop(ticket_id, name)
        ret = yield self.task_start(ticket_id, name)

        defer.returnValue(ret)

    @inlineCallbacks
    def task_rebuild(self, ticket_id, name):
        """
        Rebuild application or service.

        :param ticket_id:
        :param name:
        :return:
        """
        yield self.task_destroy(ticket_id, name)
        ret = yield self.task_start(ticket_id, name)

        defer.returnValue(ret)


    def follow_logs(self, service, ticket_id):
        def on_log(log):
            log = log[8:]
            self.task_log(ticket_id, log)

        def done(result):
           pass

        def on_err(failure):
           pass

        client = inject.instance(IDockerClient)

        d = client.logs(service.name, on_log)
        d.addCallback(done)
        d.addErrback(on_err)

        self.event_bus.once('task.failure.%s' % ticket_id, d.cancel)

        return d


    @inlineCallbacks
    def task_sync_stop(self, ticket_id, app_name, sync_ticket_id):
        s = Service()
        s.app_name = app_name
        s.name = '%s_%s_%s' % (app_name, '_rsync_', sync_ticket_id)

        yield s.inspect()

        if s.is_running():
            self.task_log(ticket_id, 'Stopping rsync container.')
            yield s.stop(ticket_id)

        if s.is_created():
            self.task_log(ticket_id, 'Destroying rsync container.')
            yield s.destroy(ticket_id)


    @inlineCallbacks
    def task_sync(self, ticket_id, app_name, service_name, volume):

        app = yield self.app_controller.get(app_name)

        config = yield app.load()


        s = Service()
        s.app_name = app_name
        s.name = '%s_%s_%s' % (app_name, '_rsync_', ticket_id)
        s.image_builder = PrebuiltImageBuilder(image='modera/rsync')
        s.ports = [873]

        if service_name:

            if not volume:
                raise VolumeNotFound('In case of service name is provided, volume name is mandatory!')

            services = config.get_services()

            service_full_name = '%s.%s' % (service_name, app_name)
            try:
                service = services[service_full_name]

                all_volumes = service.list_volumes()
                if not volume in all_volumes:
                    raise VolumeNotFound('Volume with name %s no found!' % volume)

                volume_name = volume
                s.volumes_from = service_full_name

            except KeyError:
                raise VolumeNotFound('Service with name %s was not found!' % service_name)

        else:
            s.volumes = [{
                'local': app.config['path'],
                'remote': '/volume'
            }]
            volume_name = '/volume'

        s.env = {
            'USERNAME': ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(32)),
            'PASSWORD': ''.join(random.choice(string.ascii_lowercase + string.punctuation + string.digits) for _ in range(32)),
            'ALLOW': '*'
        }

        yield s.start(ticket_id)

        defer.returnValue({
            'env': s.env,
            'container': s.name,
            'port': s.public_ports()['873'][0]['HostPort'],
            'volume': volume_name,
            'ticket_id': ticket_id
        })



    @inlineCallbacks
    def task_start(self, ticket_id, name):
        """
        Start application or service.

        :param ticket_id:
        :param name:
        :return:
        """

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

            self.task_log(ticket_id, '\n' + '*' * 50)
            self.task_log(ticket_id, '\n Service %s' % service.name)
            self.task_log(ticket_id, '\n' + '*' * 50)

            if not service.is_running():
                self.task_log(ticket_id,
                              '[%s] Service %s is not running. Starting' % (ticket_id, service.name))
                yield service.start(ticket_id)

                self.task_log(ticket_id, 'Updating container list')
                self.event_bus.fire_event('containers-updated')

                if not service.wait is False:

                    wait = service.wait
                    if wait <= 0:
                        wait = 0.2
                    if wait > 3600:
                        self.task_log(ticket_id, 'WARN: wait is to high, forcibly set to 3600s to prevent memory leaks')
                        wait = 3600

                    log_process = self.follow_logs(service, ticket_id)

                    self.task_log(ticket_id, 'Waiting for container to start. %s' % (
                        'without timeout' if wait == 0 else 'with timout %ss' % wait))

                    event = yield self.event_bus.wait_for_event('api.%s.*' % service.name, wait)
                    timeout_happenned = event is None

                    if timeout_happenned:
                        self.task_log(ticket_id, '%s seconds passed.' % wait)
                        yield service.inspect()

                        if not service.is_running():
                            self.task_log(ticket_id, 'FATAL: Service is not running after timeout. Stopping application execution.')
                            log_process.cancel()
                            defer.returnValue(False)
                        else:
                            self.task_log(ticket_id, 'Container still up. Continue execution.')
                    else:
                        sleep_time = 0.5
                        if 'my_args' in event and len(event['my_args']) == 2:
                            if event['my_args'][0] == 'in':
                                match = re.match('^([0-9]+)s$', event['my_args'][1])
                                if match:
                                    sleep_time = float(match.group(1))

                        self.task_log(ticket_id, 'Container is waiting %ss to make sure container is started.' % sleep_time)
                        yield sleep(sleep_time)

                        if not service.is_running():
                            self.task_log(ticket_id, 'FATAL: Service is not running after ready report. Stopping application execution.')
                            log_process.cancel()
                            defer.returnValue(False)
                        else:
                            self.task_log(ticket_id, 'Container still up. Continue execution.')

                    log_process.cancel()

                else:
                    yield sleep(0.2)

            else:
                self.task_log(ticket_id,
                              '[%s] Service %s is already running.' % (ticket_id, service.name))

        # ret = yield self.app_controller.list()
        ret = 'Done.'
        defer.returnValue(ret)


    @inlineCallbacks
    def task_create(self, ticket_id, name):

        """
        Create application containers without starting.

        :param ticket_id:
        :param name:
        :return:
        """

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

        # ret = yield self.app_controller.list()
        ret = 'Done.'
        defer.returnValue(ret)


    @inlineCallbacks
    def task_stop(self, ticket_id, name):
        """
        Stop application containers without starting.

        :param ticket_id:
        :param name:
        :return:
        """

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

        # ret = yield self.app_controller.list()
        ret = 'Done.'
        defer.returnValue(ret)

    @inlineCallbacks
    def task_destroy(self, ticket_id, name):

        """
        Remove application containers.

        :param ticket_id:
        :param name:
        :return:
        """

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

        # ret = yield self.app_controller.list()
        ret = 'Done.'
        defer.returnValue(ret)


    @inlineCallbacks
    def task_inspect(self, ticket_id, name, service_name):
        """
        Get inspect data of service

        :param ticket_id:
        :param name:
        :param service_name:
        :return:
        """

        self.task_log(ticket_id, '[%s] Inspecting application service %s' %
                      (ticket_id, service_name))

        app = yield self.app_controller.get(name)
        config = yield app.load()

        """
        @type config: YamlConfig
        """
        self.task_log(ticket_id, '[%s] Got response' % (ticket_id, ))

        service = config.get_service('%s.%s' % (service_name, name))
        if not service.is_created():
            defer.returnValue('Not created')
        else:
            if not service.is_inspected():
                ret = yield service.inspect()
                defer.returnValue(ret)
            else:
                defer.returnValue(service._inspect_data)


    @inlineCallbacks
    def task_deployments(self, ticket_id):
        """
        List deployments (published URLs)

        :param ticket_id:
        :return:
        """

        deployments = yield self.deployment_controller.list()

        deployment_list = []

        for deployment in deployments:
            deployment_list.append(deployment.load_data())

        ret = yield defer.gatherResults(deployment_list, consumeErrors=True)
        defer.returnValue(ret)

    #
    # @inlineCallbacks
    # def task_deployment_create(self, ticket_id, public_domain):
    # deployment = yield self.deployment_controller.create(public_domain)
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
        """
        Publish application URL.

        :param ticket_id:
        :param deployment_name:
        :param app_name:
        :return:
        """
        yield self.deployment_controller.publish_app(deployment_name, app_name)

        ret = yield self.app_controller.list()
        defer.returnValue(ret)

    @inlineCallbacks
    def task_unpublish(self, ticket_id, deployment_name):
        """
        Unpublish URL

        :param ticket_id:
        :param deployment_name:
        :return:
        """

        yield self.deployment_controller.unpublish_app(deployment_name)

        ret = yield self.app_controller.list()
        defer.returnValue(ret)

    def collect_tasks(self, ):

        tasks = {}
        for name, func in inspect.getmembers(self):
            if name.startswith('task_'):
                tasks[name[5:]] = func

        return tasks

