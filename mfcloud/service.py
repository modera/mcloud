import logging
import inject
from mfcloud.remote import ApiRpcServer
from mfcloud.txdocker import IDockerClient, DockerConnectionFailed
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks, returnValue
import txredisapi

logger = logging.getLogger('mfcloud.application')

class NotInspectedYet(Exception):
    pass


class Service(object):

    NotInspectedYet = NotInspectedYet

    client = inject.attr(IDockerClient)

    dns_server = inject.attr('dns-server')
    dns_search_suffix = inject.attr('dns-search-suffix')
    redis = inject.attr(txredisapi.Connection)

    rpc_server = inject.attr(ApiRpcServer)

    def __init__(self, **kwargs):
        self.image_builder = None
        self.name = None
        self.app_name = None
        self.volumes = None
        self.volumes_from = None
        self.ports = None
        self.command = None
        self.env = None
        self.config = None
        self.status_message = ''
        self._inspect_data = None
        self._inspected = False

        self.__dict__.update(kwargs)
        super(Service, self).__init__()



    def task_log(self, ticket_id, message):
        self.rpc_server.task_progress(message, ticket_id)

    def build_docker_config(self):
        pass


    @inlineCallbacks
    def inspect(self):
        self._inspected = True
        data = yield self.client.inspect(self.name)
        self._inspect_data = data
        defer.returnValue(self._inspect_data)

    def is_running(self):
        if not self.is_inspected():
            raise self.NotInspectedYet()
        try:
            return self.is_created() and self._inspect_data['State']['Running']
        except KeyError:
            return False

    @property
    def shortname(self):
        name_ = self.name
        if self.app_name and name_.endswith(self.app_name):
            name_ = name_[0:-len(self.app_name) - 1]
        return name_

    def ip(self):
        if not self.is_running():
            return None

        return self._inspect_data['NetworkSettings']['IPAddress']

    def image(self):
        if not self.is_created():
            return None

        return self._inspect_data['Image']

    def hosts_path(self):
        if not self.is_created():
            return None

        return self._inspect_data['HostsPath']

    def public_ports(self):
        if not self.is_running():
            return None

        return self._inspect_data['NetworkSettings']['Ports']

    def attached_volumes(self):
        if not self.is_running():
            return None

        return self._inspect_data['Volumes'].keys()

    def started_at(self):
        if not self.is_running():
            return None

        return self._inspect_data['State']['StartedAt']

    def is_web(self):
        if not self.is_running():
            return None

        if not 'NetworkSettings' in self._inspect_data or not 'Ports' in self._inspect_data['NetworkSettings'] or \
            not self._inspect_data['NetworkSettings']['Ports']:
            return False

        return u'80/tcp' in self._inspect_data['NetworkSettings']['Ports']

    def is_created(self):
        if not self.is_inspected():
            raise self.NotInspectedYet()

        return not self._inspect_data is None

    @inlineCallbacks
    def start(self, ticket_id):
        id_ = yield self.client.find_container_by_name(self.name)

        self.task_log(ticket_id, '[%s][%s] Starting service' % (ticket_id, self.name))
        self.task_log(ticket_id, '[%s][%s] Service resolve by name result: %s' % (ticket_id, self.name, id_))

        # container is not created yet
        if not id_:
            self.task_log(ticket_id, '[%s][%s] Service not created. Creating ...' % (ticket_id, self.name))
            yield self.create(ticket_id)
            id_ = yield self.client.find_container_by_name(self.name)

        self.task_log(ticket_id, '[%s][%s] Starting service...' % (ticket_id, self.name))

        config = {
            "Dns": [self.dns_server],
            "DnsSearch": '%s.%s' % (self.app_name, self.dns_search_suffix)
        }

        if self.volumes_from:
            config['VolumesFrom'] = self.volumes_from

        if self.ports:
            config['PortBindings'] = dict([(port, [{}]) for port in self.ports])

        if self.volumes and len(self.volumes):
            config['Binds'] = ['%s:%s' % (x['local'], x['remote']) for x in self.volumes]

        self.task_log(ticket_id, 'Startng container with config: %s' % config)

        #config['Binds'] = ["/home/alex/dev/mfcloud/examples/static_site1/public:/var/www"]

        yield self.client.start_container(id_, ticket_id=ticket_id, config=config)

        # inspect and return result
        ret = yield self.inspect()

        defer.returnValue(ret)


    @inlineCallbacks
    def stop(self, ticket_id):

        id = yield self.client.find_container_by_name(self.name)

        yield self.client.stop_container(id, ticket_id=ticket_id)

        ret = yield self.inspect()
        defer.returnValue(ret)

    @inlineCallbacks
    def _generate_config(self, image_name):
        config = {
            "Hostname": self.name,
            "Image": image_name,
        }

        vlist = yield self.redis.hgetall('vars')

        if self.env:
            vlist.update(self.env)

        config['Env'] = ['%s=%s' % x for x in vlist.items()]

        if self.ports:
            config['ExposedPorts'] = dict([(port, {}) for port in self.ports])

        if self.volumes and len(self.volumes):
            config['Volumes'] = dict([
                (x['remote'], {}) for x in self.volumes
            ])

        defer.returnValue(config)


    @inlineCallbacks
    def create(self, ticket_id):

        image_name = yield self.image_builder.build_image(ticket_id=ticket_id)

        config = yield self._generate_config(image_name)
        yield self.client.create_container(config, self.name, ticket_id=ticket_id)

        ret = yield self.inspect()
        defer.returnValue(ret)

    @inlineCallbacks
    def destroy(self, ticket_id):
        id_ = yield self.client.find_container_by_name(self.name)
        yield self.client.remove_container(id_, ticket_id=ticket_id)

        ret = yield self.inspect()
        defer.returnValue(ret)

    def is_inspected(self):
        return self._inspected




