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


class FicloudDeployment():

    def __init__(self, config_file='~/.ficloud.yml'):
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

        self.project_dir = None
        self.project_name = None
        self.env_name = None
        self._project = None

    def init(self, project_dir, env_name, project_name=None):
        self.project_dir = project_dir
        self.env_name = env_name

        if not project_name:
            project_name = os.path.basename(os.getcwd())
            project_name = re.sub(r'[^a-zA-Z0-9]', '', project_name)

        self.project_name = project_name


    def _get_fig_project(self):

        if not self.env_name:
            raise ValueError('env is not specified!')

        if not self.project_dir:
            raise ValueError('project_dir is not specified!')

        if not self.project_name:
            raise ValueError('project_name is not specified!')

        os.chdir(self.project_dir)
        config = yaml.load(open('fig.yml'))

        config = transform_config(config, env=self.env_name)
        project = Project.from_config(self.project_name, config, self.client)
        return project

    @property
    def host(self):
        if not 'host' in self.config:
            raise ValueError('host is not selected!')
        return self.config['host']

    @property
    def project(self):
        if not self._project:
            self._project = self._get_fig_project()
        return self._project

    def use_host(self, host, **kwargs):
        """
        Sets currently used host
        """
        self.config['host'] = host
        env.host_string = host

        self.save_config()

    def status(self, **kwargs):

        table = PrettyTable(["Service", "Status"])

        for service in self.project.services:
            table.add_row((service.name, format_service_status(service)))

        print(table)

    def start(self, services=None, logs=True, **kwargs):

        project = self.project

        all_containers = []
        for service in project.get_services(services):
            if len(service.containers(stopped=True)) == 0:
                service.create_container()

            all_containers += service.containers(stopped=True)

        log_printer = None
        if logs:
            log_printer = LogPrinter(all_containers)

        project.start(services)

        if log_printer:
            try:
                print("Following logs from containers.")
                log_printer.run()
            except KeyboardInterrupt:
                print("Interrupted by Ctrl + C. Containers are still running. Use `ficloud stop` to stop them.")



    def stop(self, services=None, **kwargs):
        project = self.project
        project.stop(services)

    def destroy(self, services=None, **kwargs):
        project = self.project
        project.stop(services)
        project.kill(services)
        project.remove_stopped(services)

    def rebuild(self, services=None, **kwargs):
        pass

    def logs(self, services=None, **kwargs):
        project = self.project

        containers = project.containers(service_names=services, stopped=True)
        LogPrinter(containers, attach_params={'logs': True}).run()

    def get_volumes(self, project):
        volumes = {}
        for service in project.get_services():

            for c in service.containers(stopped=True):
                for volume, dir in c.inspect()['Volumes'].items():
                    volumes['%s@%s' % (c.name, volume)] = dir
        return volumes

    def list_volumes(self, **kwargs):

        table = PrettyTable(["Volume", "Mount directory"])

        project = self.project

        for volume, dir in self.get_volumes(project).items():
            table.add_row((
                volume,
                dir
            ))

        print(table)


    def remote(self, command, **kwargs):
        run('ficloud-server %s' % ' '.join(command))


    def save_config(self):
        with open(self.ficloud_yml, 'w+') as f:
            yaml.dump(self.config, f)
