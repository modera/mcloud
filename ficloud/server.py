import os
import sys
from pywizard.compat.os_debian.package_apt import AptPackageProvider
from pywizard.compat.os_linux.sudo import require_sudo
from pywizard.core.resource_aggregate import aggregate_config
from pywizard.core.templating import jinja_templates, tpl
from pywizard.resources.git import git_repo, git_clone
from pywizard.resources.package import register_package_provider
import re

from fig.cli.command import Command
from fig.packages.docker import Client
from fig.project import Project
import yaml

from pywizard.api import python_package, package, directory, file_
from pywizard.core.decorators import pywizard_apply, rollback, resource_set
from pywizard.resources.service import service
from pywizard.utils.process import run


class FicloudServer():

    def __init__(self):
        self.client = Client()
        self.balancer_root = ''

    def _get_git_dir(self):
        return os.path.expanduser('~/apps')

    def _get_app_git_dir(self, name):
        return '%s/%s' % (self._get_git_dir(), name)

    def _get_deployment_dir(self):
        return os.path.expanduser('~/deploy')

    def _get_app_deployment_dir(self, name, version):
        return '%s/%s/%s' % (self._get_deployment_dir(), name, version)

    def create_app(self, name, **kwargs):
        """
        Creates new application. Basically, creates new git repo.

        """
        with pywizard_apply():
            git_repo(self._get_app_git_dir(name))

    def deploy_app_version(self, name, version, domain):
        """

        """
        target_dir = self._get_app_deployment_dir(name, version)
        repo = self._get_app_git_dir(name)

        with pywizard_apply():
            directory(os.path.dirname(target_dir))
            git_clone(repo, target_dir)

            run('cd %s && fig up -d' % target_dir)

        self.balancer_set(domain, target_dir)


    def list_apps(self, **kwargs):
        if not os.path.exists(self._get_git_dir()):
            print 'No apps yet'
        else:
            print('\n'.join(filter(os.path.isdir, [x for x in os.listdir(self._get_git_dir()) if not x[0] == '.'])))

    def list_app_versions(self, name):
        app_dir = '%s/%s' % (self._get_deployment_dir(), name)
        if not os.path.exists(app_dir):
            print 'App has no versions deployed'
        else:
            print('\n'.join(filter(os.path.isdir, [x for x in os.listdir(app_dir) if not x[0] == '.'])))


    def get_balancer_destinations(self, app_name, app_version, service, port):

        config = yaml.load(open('%s/fig.yml' % self._get_app_deployment_dir(app_name, app_version)))

        project = Project.from_config(Command().project_name, config, self.client)

        service_ports = []
        for c in project.get_service(service).containers():
            if c.is_running:
                ports = c.inspect()['NetworkSettings']['Ports']
                service_ports.append(('127.0.0.1', int(ports['%s/tcp' % port][0]['HostPort'])))

        return service_ports

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

        app_name = result.group(1)
        app_version = result.group(3)
        service_name = result.group(4)
        service_port = result.group(5)
        config = {
            'domain': domain,

            'app_name': app_name,

            'servers': self.get_balancer_destinations(app_name, app_version, service_name, service_port),
            'static_folders': [],

            'target': {
                'host': result.group(2) or 'localhost',
                'service': service_name,
                'port': service_port,
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

