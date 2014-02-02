from fig.cli.command import Command
from fig.packages.docker import Client
from fig.project import Project
import yaml


class FigaroServer():

    def __init__(self):
        self.client = Client()

    def dump_ports(self, service, port, **kwargs):

        config = yaml.load(open('fig.yml'))

        project = Project.from_config(Command().project_name, config, self.client)

        service_ports = []
        for c in project.get_service(service).containers():
            if c.is_running:
                ports = c.inspect()['NetworkSettings']['Ports']
                service_ports.append(int(ports['%s/tcp' % port][0]['HostPort']))

        print(service_ports)
        yaml.dump({'ports': service_ports}, open('app.yml', 'w+'))


    def balancer_install(self, **kwargs):
