from fabric.api import run, env
import os
import yaml
from os.path import expanduser
import cuisine as remote

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


    def app_create(self, name, **kwargs):

        if not remote.dir_exists('apps'):
            run('mkdir apps')

        if not remote.dir_exists('apps/%s' % name):
            run('git init --bare apps/%s' % name)
        else:
            print('Remote repo already exists')


    def app_remove(self, name, **kwargs):

        if remote.dir_exists('apps/%s' % name):
            run('rm -rf apps/%s' % name)
        else:
            print('Remote repo does not exist')


    def app_list(self, **kwargs):
        print(env.hosts)
        if remote.dir_exists('apps'):
            run('ls -l apps')


    def save_config(self):
        with open(self.ficloud_yml, 'w+') as f:
            yaml.dump(self.config, f)
