import inject
from mfcloud.application import ApplicationController, Application
from twisted.internet import defer, reactor


class TaskService():

    app_controller = inject.attr(ApplicationController)
    """
    @type app_controller: ApplicationController
    """

    def task_init_app(self, ticket_id, name, path):

        d = self.app_controller.create(name, path)

        def done(app):
            return not app is None

        d.addCallback(done)
        return d

    def task_list_app(self, ticket_id):
        d = self.app_controller.list()

        def done(apps):
            return [(name, apps.config['path']) for name, apps in apps.items()]

        d.addCallback(done)
        return d

    def task_del_app(self, ticket_id, name):
        d = self.app_controller.remove(name)

        # d.addCallback(done)
        return d

    def task_app_status(self, ticket_id, name):
        d = self.app_controller.get(name)

        def on_result(config):
            """
            @type config: YamlConfig
            """

            data = []
            for service in config.get_services().values():

                # is_created = yield service.is_created()
                # is_running = yield service.is_running()

                data.append([
                    service.name,
                    # is_created,
                    # is_running
                    False,
                    False,
                ])

            return data

        d.addCallback(lambda app: app.load())
        d.addCallback(on_result)
        return d

    def register(self, rpc_server):

        rpc_server.tasks.update({
            'init': self.task_init_app,
            'list': self.task_list_app,
            'status': self.task_app_status,
            'remove': self.task_del_app,
        })