from fig.cli.log_printer import LogPrinter
from fig.packages.docker import Client
from prettytable import PrettyTable
from fabric.api import run, env
from fig.project import Project
import os
import yaml
from os.path import expanduser
import cuisine as remote
import re
from ficloud.fig_ext import transform_config
from ficloud.util import format_service_status


class NoHostSelected(Exception):
    pass

class FicloudClient():

    def __init__(self, config_file='~/.ficloud.yml', env_name='dev'):
        self.ficloud_yml = expanduser(config_file)

        # load config
        if os.path.exists(self.ficloud_yml):
            with open(self.ficloud_yml) as f:
                self.config = yaml.load(f)
                if self.config is None:
                    self.config = {}
        else:
            self.config = {}

        if 'host' in self.config:
            env.host_string = self.config['host']

        self.client = Client()


    def _get_fig_project(self, env_name):
        config = yaml.load(open('fig.yml'))
        project_name = os.path.basename(os.getcwd())
        project_name = re.sub(r'[^a-zA-Z0-9]', '', project_name)

        config = transform_config(config, env=env_name)

        project = Project.from_config(project_name, config, self.client)
        return project

    @property
    def host(self):
        if not 'host' in self.config:
            raise NoHostSelected('host is not selected!')
        return self.config['host']

    def use_host(self, host, **kwargs):
        """
        Sets currently used host
        """
        self.config['host'] = host
        env.host_string = host

        self.save_config()

    def status(self, env_name='dev', **kwargs):

        table = PrettyTable(["Service", "Status"])

        for service in self._get_fig_project(env_name).services:
            table.add_row((service.name, format_service_status(service)))

        print(table)

    def start(self, services, logs=False, env_name='dev', **kwargs):

        project = self._get_fig_project(env_name)

        for service in project.services:
            if len(service.containers(stopped=True)) == 0:
                service.create_container()
            else:
                service.start()

    def stop(self, services, env_name='dev', **kwargs):
        project = self._get_fig_project(env_name)
        project.stop(services)

    def destroy(self, services, env_name='dev', **kwargs):
        project = self._get_fig_project(env_name)
        project.stop(services)
        project.kill(services)
        project.remove_stopped(services)

    def rebuild(self, services, env_name='dev', **kwargs):
        pass

    def logs(self, services, env_name='dev', **kwargs):
        project = self._get_fig_project(env_name)

        containers = project.containers(service_names=services, stopped=True)
        LogPrinter(containers, attach_params={'logs': True}).run()

    def list_volumes(self, env_name='dev', **kwargs):

        table = PrettyTable(["Volume", "Mount directory"])

        for service in self._get_fig_project(env_name).get_services():

            for c in service.containers(stopped=True):
                for volume, dir in c.inspect()['Volumes'].items():
                    table.add_row((
                        '%s@%s' % (c.name, volume),
                        dir
                    ))

        print(table)


    def remote(self, command, **kwargs):
        run('ficloud-server %s' % ' '.join(command))


    def save_config(self):
        with open(self.ficloud_yml, 'w+') as f:
            yaml.dump(self.config, f)
