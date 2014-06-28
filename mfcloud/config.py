from abc import abstractmethod
from mfcloud.container import PrebuiltImageBuilder, DockerfileImageBuilder
from mfcloud.util import Interface
import os
from os.path import dirname
import yaml
from .service import Service
from voluptuous import Schema, MultipleInvalid
from voluptuous import Required


class IConfig(Interface):

    @abstractmethod
    def get_services(self):
        """
        :rtype:
        """
        pass

class ConfigParseError(Exception):
    pass


class UnknownServiceError(Exception):
    pass


class YamlConfig(IConfig):

    def __init__(self, file=None, source=None, app_name=None):

        if not file is None:
            if not os.path.exists(str(file)):
                raise ValueError('Bad config file given!')

            self._file = str(file)
            self._source = None

        elif not source is None:
            self._source = source
            self._file = None

        self.app_name = app_name
        self.services = {}

    def get_services(self):
        """
        @rtype: dict[str, Service]
        """
        return self.services

    def get_service(self, name):
        """
        @rtype: Service
        """
        if not name in self.services:
            raise UnknownServiceError('Unknown service %s' % name)

        return self.services[name]

    def load(self):

        try:
            if not self._file is None:
                with open(self._file) as f:
                    cfg = yaml.load(f)

                path = dirname(self._file)
            else:
                cfg = yaml.load(self._source)
                path = None

            self.validate(config=cfg)

            self.process(config=cfg, path=path, app_name=self.app_name)


        except ValueError as e:
            raise ConfigParseError('Failed to parse %s: %s' % (self._file, e.message))


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
            if path is None:
                service.status_message += '\nService %s requested to attach volumes, but ' \
                                          'yaml config was uploaded separately ' \
                                          'without source files attached.'
                return

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
            if path is None:
                raise ConfigParseError('Service %s image requested build container image using Dockerfile but, '
                                       'yaml config was uploaded separately without source files attached.' % service)
            service.image_builder = DockerfileImageBuilder(path=os.path.join(path, config['build']))
        else:
            raise ValueError('Specify image source for service %s: image or build' % service.name)

    def process(self, config, path, app_name=None):

        for name, service in config.items():
            if app_name:
                name = '%s.%s' % (name, app_name)

            s = Service()
            s.app_name = self.app_name
            s.name = name

            self.process_image_build(s, service, path)
            self.process_volumes_build(s, service, path)
            self.process_command_build(s, service, path)
            self.process_env_build(s, service, path)

            self.services[name] = s

            if s.volumes:
                volume_service_name = '_volumes_%s' % name
                volume_service = Service(
                    volumes_from=name,
                    name=volume_service_name,
                    ports=['22/tcp'],
                    image_builder=PrebuiltImageBuilder('ribozz/rsync')
                )
                self.services[volume_service_name] = volume_service
