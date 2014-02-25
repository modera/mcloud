from fig.packages.docker import Client
from prettytable import PrettyTable
from fabric.api import run, env
from fig.project import Project
import os
import yaml
from os.path import expanduser
import cuisine as remote
import re


class NoHostSelected(Exception):
    pass

class FicloudClient():

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

    def _get_fig_project(self):
        config = yaml.load(open('fig.yml'))
        project_name = os.path.basename(os.getcwd())
        project_name = re.sub(r'[^a-zA-Z0-9]', '', project_name)
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

    def status(self, **kwargs):
        print('\n')
        print('*' * 40)
        try:
            print('Host: %s' % self.host)
        except NoHostSelected:
            print 'Host not selected'
        print('*' * 40)

    def list_volumes(self, **kwargs):

        table = PrettyTable(["Service", "Container", "Volume"])

        last_service = None
        for service in self._get_fig_project().get_services():

            for c in service.containers(stopped=True):
                table.add_row((
                    service.name if last_service != service.name else '',
                    c.name,
                    str(c.inspect()['Volumes'])
                ))

            last_service = service.name

        print(table)


    def remote(self, command, **kwargs):
        run('ficloud-server %s' % ' '.join(command))


    def save_config(self):
        with open(self.ficloud_yml, 'w+') as f:
            yaml.dump(self.config, f)
