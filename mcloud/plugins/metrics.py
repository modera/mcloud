import logging
from autobahn.twisted.util import sleep
import inject
from mcloud.application import ApplicationController
from mcloud.events import EventBus
from mcloud.plugins import Plugin
from mcloud.txdocker import IDockerClient
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall
import txredisapi
from twisted.python import log

logger = logging.getLogger('mcloud.plugin.metrics')


class MetricsPlugin(Plugin):
    eb = inject.attr(EventBus)
    app_controller = inject.attr(ApplicationController)
    redis = inject.attr(txredisapi.Connection)
    client = inject.attr(IDockerClient)

    prev_cpu_total = 0
    prev_cpu_services = {}

    def read_usage_value(self, file_name):
        try:
            with open(file_name) as f:
                return int(f.read())
        except IOError:
            return 0

    def get_memory_usage(self, _id):
        return self.read_usage_value('/sys/fs/cgroup/memory/docker/%s/memory.usage_in_bytes' % _id) / (1024 * 1024)

    def _get_cpu_values(self, ids):
        return (
            self.read_usage_value('/sys/fs/cgroup/cpuacct/cpuacct.usage'),
            dict([(_id, self.read_usage_value('/sys/fs/cgroup/cpuacct/docker/%s/cpuacct.usage' % _id)) for _id in ids])
        )

    def get_cpu_usages(self, ids):
        total, services = self._get_cpu_values(ids)
        prev_total, prev_services = self.prev_cpu_total, self.prev_cpu_services

        self.prev_cpu_total = total
        self.prev_cpu_services = services

        usages = dict([(_id, 0) for _id in ids])

        if not prev_total:
            return usages

        delta_total = total - prev_total

        for _id in ids:
            if not _id in prev_services:
                continue

            id_delta = services[_id] - prev_services[_id]
            usages[_id] = float(id_delta) / float(delta_total) * 100

        return usages

    @inlineCallbacks
    def calc_stats(self):

        apps_list = yield self.app_controller.list()

        services = []

        for app in apps_list:
            for service in app['services']:
                if not service['running']:
                    continue
                services.append(service['name'])

        ids = yield self.client.find_containers_by_names(services)

        cpu_usages = yield self.get_cpu_usages(ids.values())

        usage = {}
        for name, _id in ids.items():
            usage[name] = '%s;%s' % (self.get_memory_usage(_id), cpu_usages[_id])

        logger.info('Dumping metrics for containers')

        yield self.redis.delete('metrics')
        if usage:
            yield self.redis.hmset('metrics', usage)

    def __init__(self, interval=1):
        super(MetricsPlugin, self).__init__()

        lc = LoopingCall(self.calc_stats)
        lc.start(interval)

        logger.info('Metrics plugin started')