import inject
from mfcloud.txdocker import IDockerClient


class Service(object):


    client = inject.attr(IDockerClient)

    image_builder = None
    name = None
    volumes = None
    command = None
    env = None
    config = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        super(Service, self).__init__()

        self._inspect_data = None

    def build_docker_config(self):
        pass

    def inspect(self):

        d = self.client.find_container_by_name(self.name)

        d.addCallback(self.client.inspect)

        return d

    def is_running(self):
        d = self.inspect()

        def on_inspect_done(inspect_data):
            if not inspect_data:
                return False
            return inspect_data['State']['Running']

        d.addCallback(on_inspect_done)
        return d

    def is_created(self):
        d = self.inspect()

        def on_inspect_done(inspect_data):
            return not inspect_data is None

        d.addCallback(on_inspect_done)
        return d

    def start(self, ticket_id):

        d = self.client.find_container_by_name(self.name)

        def on_result(id):
            return self.client.start_container(id, ticket_id=ticket_id)

        d.addCallback(on_result)

        return d

    def stop(self, ticket_id):

        d = self.client.find_container_by_name(self.name)

        def on_result(id):
            return self.client.stop_container(id, ticket_id=ticket_id)

        d.addCallback(on_result)

        return d

    def create(self, ticket_id):

        d = self.image_builder.build_image(ticket_id=ticket_id)

        def image_ready(image_name):
            config = {
                "Hostname": self.name,
                "Image": image_name
            }

            return self.client.create_container(config, self.name, ticket_id=ticket_id)

        d.addCallback(image_ready)

        return d

    def destroy(self, ticket_id):

        d = self.client.find_container_by_name(self.name)

        def on_result(id):
            return self.client.remove_container(id, ticket_id=ticket_id)

        d.addCallback(on_result)

        return d

    def is_inspected(self):
        return not self._inspect_data is None




