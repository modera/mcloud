import sys
from pywizard.compat.os_debian.package_apt import AptPackageProvider
from pywizard.compat.os_linux.sudo import require_sudo
from pywizard.core.resource_aggregate import aggregate_config
from pywizard.core.templating import jinja_templates, tpl
from pywizard.resources.package import register_package_provider
import re

from fig.cli.command import Command
from fig.packages.docker import Client
from fig.project import Project
import yaml

from pywizard.api import python_package, package, directory, file_
from pywizard.core.decorators import pywizard_apply, rollback, resource_set
from pywizard.resources.service import service


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

    def balancer_remove(self, domain, **kwargs):
        require_sudo('Run this script as sudo')

        with pywizard_apply():

            nginx_service = service('nginx')

            with rollback():
                with resource_set('nginx_cfg'):
                    self.nginx_cfg_file({}, domain, nginx_service)

    def nginx_cfg_file(self, config, domain, nginx_service):
        cfg = file_(
            '/etc/nginx/conf.d/%s.conf' % domain,
            content=tpl('nginx.conf', context=config),
        )
        cfg.on_create = (nginx_service.reload,)
        cfg.on_update = (nginx_service.reload,)
        cfg.on_remove = (nginx_service.reload,)

    def balancer_set(self, domain, path, **kwargs):

        p = re.compile(r'^[\w\-\._]+$')
        result = p.match(domain)

        if not result:
            print('\nEnter valid domain name\n')
            sys.exit(1)

        p = re.compile(r'^([\w\-]+)@([\w\-\._]+)?\/([\w\-]+)\/([\w\-]+):(\d+)$')
        result = p.match(path)

        if not result:
            print('\nPath should be in form: appname@host/app_version/service:port\n')
            sys.exit(1)

        config = {
            'domain': domain,

            'app_name': result.group(1),

            'servers': [],
            'static_folders': [],

            'target': {
                'host': result.group(2) or 'localhost',
                'service': result.group(4),
                'port': result.group(5),
            }
        }

        config['servers'].append({
            'ip': '127.0.0.1',
            'port': '8000'
        })

        register_package_provider(AptPackageProvider)
        require_sudo('Run this script as sudo')

        with jinja_templates('ficloud'):
            with pywizard_apply():

                package('nginx')

                nginx_service = service('nginx')

                self.nginx_cfg_file(config, domain, nginx_service)

