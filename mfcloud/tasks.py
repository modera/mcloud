import inject
from mfcloud.application import ApplicationController, Application


class TaskService():

    app_controller = inject.attr(ApplicationController)

    def task_init_app(self, name, path):

        d = self.app_controller.create(name, path)

        def done(app):
            return not app is None

        d.addCallback(done)
        return d

    def task_list_app(self):
        d = self.app_controller.list()

        def done(apps):
            return [(name, apps.config['path']) for name, apps in apps.items()]

        d.addCallback(done)
        return d