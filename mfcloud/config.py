from abc import abstractmethod
from mfcloud.util import Interface
import os
from os.path import dirname
import yaml
from .service import Service
from voluptuous import Schema, MultipleInvalid
from voluptuous import Required, All, Length, Range


class PrebuiltImageBuilder(object):
    def __init__(self, image):
        super(PrebuiltImageBuilder, self).__init__()

        self.image = image


class DockerfileImageBuilder(object):
    def __init__(self, path):
        super(DockerfileImageBuilder, self).__init__()
        self.path = path


class IConfig(Interface):

    @abstractmethod
    def get_services(self):
        """
        :rtype:
        """
        pass

class YamlConfig(IConfig):

    def __init__(self, file=None):
        super(YamlConfig, self).__init__()

        if not file is None and not os.path.exists(str(file)):
            raise ValueError('Bad config file given!')

        self._file = str(file)

        self.services = {}

    def get_services(self):
        return self.services


    def load(self):

        with open(self._file) as f:
            cfg = yaml.load(f)

            self.validate(config=cfg)
            self.process(config=cfg, path=dirname(self._file))


    def validate(self, config):
        try:
            Schema({
                Required(str): {
                    'image': str,
                    'build': str,

                    'volumes': {
                        str: str
                    },

                    'env': {
                        str: str
                    }
                }
            })(config)

            for service in config.values():
                if not 'image' in service and not 'build' in service:
                    raise ValueError('You should define "image" or "build" as a vay to build a container.')
        except MultipleInvalid as e:
            raise ValueError(e)

        return True

    def process_command_build(self, service, config, path):
        if 'cmd' in config and config['cmd'] and  len(str(config['cmd']).strip()) > 0:
            service.command = str(config['cmd']).strip()

    def process_volumes_build(self, service, config, path):
        service.volumes = []

        if 'volumes' in config and len(config['volumes']):
            for local_path, container_path in config['volumes'].items():
                service.volumes.append({
                    'local': os.path.join(path, local_path),
                    'remote': container_path
                })

    def process_env_build(self, service, config, path):
        service.env = {}

        if 'env' in config and len(config['env']):
            for name, val in config['env'].items():
                service.env[name] = str(val)

    def process_image_build(self, service, config, path):

        # way to build
        if 'image' in config:
            service.image_builder = PrebuiltImageBuilder(image=config['image'])
        elif 'build' in config:
            service.image_builder = DockerfileImageBuilder(path=os.path.join(path, config['build']))
        else:
            raise ValueError('Specify image source for service %s: image or build' % service.name)

    def process(self, config, path):

        for name, service in config.items():

            s = Service()
            s.name = name

            self.process_image_build(s, service, path)
            self.process_volumes_build(s, service, path)
            self.process_command_build(s, service, path)

            self.services[name] = service
