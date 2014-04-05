from fig.cli.log_printer import LogPrinter
from fig.cli.socketclient import SocketClient
from fig.packages.docker import Client
import getpass
import json
from prettytable import PrettyTable
from fabric.api import run, env
import fabric
from fig.project import Project
from fabric.contrib.console import confirm
import os
import yaml
from os.path import expanduser
import cuisine as remote
import re
from mfcloud.fig_ext import transform_config
from mfcloud.util import format_service_status


def project_name_by_dir():
    project_name = os.path.basename(os.getcwd())
    project_name = re.sub(r'[^a-zA-Z0-9]', '', project_name)
    return project_name


class MfcloudDeployment():
    def __init__(self, config_file='~/.mfcloud.yml'):
        self.mfcloud_yml = expanduser(config_file)

        # load config
        if os.path.exists(self.mfcloud_yml):
            with open(self.mfcloud_yml) as f:
                self.config = yaml.load(f)
                if self.config is None:
                    self.config = {}
        else:
            self.config = {}

        if 'host' in self.config:
            env.host_string = self.config['host']

        env.output_prefix = False
        fabric.state.output.running = False

        self.client = Client()

        self.project_dir = None
        self.project_name = None
        self.env_name = None
        self._project = None

    def init(self, project_dir, env_name, project_name=None):
        self.project_dir = project_dir
        self.env_name = env_name

        if not project_name:
            project_name = project_name_by_dir()

        self.project_name = project_name


    def _get_fig_project(self):

        if not self.env_name:
            raise ValueError('env is not specified!')

        if not self.project_dir:
            raise ValueError('project_dir is not specified!')

        if not self.project_name:
            raise ValueError('project_name is not specified!')

        os.chdir(self.project_dir)
        with open('mfcloud.yml') as f:
            config = yaml.load(f)

        config = transform_config(config['services'], env=self.env_name)
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

    def pull_volumes(self, volumes, **kwargs):
        return self.push_volumes(volumes, reverse=True, **kwargs)

    def push_volumes(self, volumes, reverse=False, **kwargs):
        for volume in volumes:

            p = re.compile(r'^([\w\-]+):([\w\d/_-]+)@([\w\-]+)#([\w\-]+)$')
            result = p.match(volume)

            if not result:
                print('\nVolume should be of format service:/volume/path@app#version')
                return

            (service, volume_name, app, version) = result.groups()

            data = run('mfcloud-server app %s %s volumes --json' % (app, version))
            data = json.loads(data)

            volume_key = '%s@%s' % (service, volume_name)

            if not volume_key in data:
                ValueError('Remote volume %s not found on remote server' % volume_name)

            local_data = self.get_volumes()
            if not volume_key in local_data:
                ValueError('Remote volume %s not found on local machine' % volume_name)

            # reverse = pull operation
            if reverse:
                (data, local_data) = (local_data, data)

            cmd = 'sudo rsync -e "ssh -i /home/%(user)s/.ssh/id_rsa" --delete -vv -r -p --numeric-ids -e ssh' \
                  ' --rsync-path="sudo rsync" %(local_path)s/ %(host_string)s:%(remote_path)s' % {
                      'user': getpass.getuser(),
                      'host_string': env.host_string,
                      'local_path': local_data[volume_key],
                      'remote_path': data[volume_key]
                  }

            os.system(cmd)


    def status(self, **kwargs):

        table = PrettyTable(["Service", "Status"])

        for service in self.project.services:
            table.add_row((service.name, format_service_status(service)))

        print(table)

    def run(self, service, command, disable_tty=False, **kwargs):

        service = self.project.get_service(service)

        container = service.create_container(one_off=True, **{
            'command': command,
            'tty': not disable_tty,
            'stdin_open': True,
        })

        with self._attach_to_container(container.id, raw=not disable_tty) as c:
            service.start_container(container, ports=None)
            c.run()

    def _attach_to_container(self, container_id, raw=False):
        socket_in = self.client.attach_socket(container_id, params={'stdin': 1, 'stream': 1})
        socket_out = self.client.attach_socket(container_id, params={'stdout': 1, 'logs': 1, 'stream': 1})
        socket_err = self.client.attach_socket(container_id, params={'stderr': 1, 'logs': 1, 'stream': 1})

        return SocketClient(
            socket_in=socket_in,
            socket_out=socket_out,
            socket_err=socket_err,
            raw=raw,
        )

    def start(self, services=None, logs=True, rebuild=False, **kwargs):

        project = self.project

        if rebuild:
            project.stop(services)
            project.remove_stopped(services)
            project.build(services)

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
                print("Interrupted by Ctrl + C. Containers are still running. Use `mfcloud stop` to stop them.")


    def stop(self, services=None, **kwargs):
        project = self.project
        project.stop(services)

    def destroy(self, services=None, **kwargs):
        project = self.project
        project.stop(services)
        project.kill(services)
        project.remove_stopped(services)

    def rebuild(self, services=None, **kwargs):
        self.start(services, rebuild=True, logs=False)

    def logs(self, services=None, **kwargs):
        project = self.project

        containers = project.containers(service_names=services, stopped=True)
        LogPrinter(containers, attach_params={'logs': True}).run()

    def get_volumes(self, **kwargs):
        volumes = {}
        for service in self.project.get_services():

            for c in service.containers(stopped=True):
                for volume, dir in c.inspect()['Volumes'].items():
                    volumes['%s@%s' % (service.name, volume)] = dir
        return volumes

    def list_volumes(self, **kwargs):

        if kwargs['json']:
            print(json.dumps(self.get_volumes()))
            return

        table = PrettyTable(["Volume", "Mount directory"])
        for volume, dir in self.get_volumes().items():
            table.add_row((
                volume,
                dir
            ))

        print(table)


    def remote(self, command, **kwargs):
        run('mfcloud-server %s' % ' '.join(command))


    def save_config(self):
        with open(self.mfcloud_yml, 'w+') as f:
            yaml.dump(self.config, f)
