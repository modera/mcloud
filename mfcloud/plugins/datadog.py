import logging
from dogapi.http import DogHttpApi
import inject
from mfcloud.application import ApplicationController
from mfcloud.events import EventBus
from mfcloud.plugins import Plugin
from twisted.internet.defer import inlineCallbacks
import txredisapi
from twisted.python import log


class DatadogPlugin(Plugin):
    eb = inject.attr(EventBus)
    app_controller = inject.attr(ApplicationController)

    def __init__(self):
        super(DatadogPlugin, self).__init__()
        self.eb.on('task.start', self.task_start)

        log.msg('Datadog plugin started')

        self.api = DogHttpApi(api_key='a3b62138aac259c03053eeea0567f008')

    def task_start(self, name, data):
        log.msg('Sending datadog task start event: %s' % data['name'])
        self.api.event(title='Task on server started: %s' % data['name'], text='Args: %s' % str(data['args']))

