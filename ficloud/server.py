import re
from fig.cli.command import Command
from fig.packages.docker import Client
from fig.project import Project
import yaml


class FicloudServer():

    def __init__(self, balancer_root='~/apps/balancer/conf.d'):
        self.client = Client()
        self.balancer_root = ''

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

    def balancer_set(self, domain, path, **kwargs):

        p = re.compile(r'([\w\-]+)@([\w\-\._]+)?\/([\w\-]+)\/([\w\-]+):(\d+)')
        result = p.match(path)

        app_name = result.group(1)
        app_host = result.group(2) or 'localhost'
        app_version = result.group(3)
        app_service = result.group(4)
        app_service_port = result.group(5)

        print(domain, app_name, app_host, app_version, app_service, app_service_port)

        client = Client()

        if not client.images(name='dockerfile/nginx'):
            print('Importing dockerfile/nginx image ...')
            client.import_image(image='dockerfile/nginx')



