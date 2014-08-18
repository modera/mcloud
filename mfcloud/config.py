from collections import OrderedDict
from logging import info
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


class OrderedDictYAMLLoader(yaml.Loader):
    """
    A YAML loader that loads mappings into ordered dictionaries.
    """

    def __init__(self, *args, **kwargs):
        yaml.Loader.__init__(self, *args, **kwargs)

        self.add_constructor(u'tag:yaml.org,2002:map', type(self).construct_yaml_map)
        self.add_constructor(u'tag:yaml.org,2002:omap', type(self).construct_yaml_map)

    def construct_yaml_map(self, node):
        data = OrderedDict()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            self.flatten_mapping(node)
        else:
            raise yaml.constructor.ConstructorError(None, None,
                'expected a mapping node, but found %s' % node.id, node.start_mark)

        mapping = OrderedDict()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError, exc:
                raise yaml.constructor.ConstructorError('while constructing a mapping',
                    node.start_mark, 'found unacceptable key (%s)' % exc, key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping

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
        self.services = OrderedDict()

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
                    cfg = yaml.load(f, OrderedDictYAMLLoader)

                path = dirname(self._file)
            else:
                cfg = yaml.load(self._source, OrderedDictYAMLLoader)
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

            volume_service_name = '_volumes_%s' % name

            volumes = None

            if path:
                keys_path = os.path.join(path, '.mfcloud/keys.txt')
                if os.path.exists(keys_path):
                    volumes = [{
                        'local': keys_path,
                        'remote': '/root/.ssh/authorized_keys'
                    }]

            volume_service = Service(
                volumes_from=name,
                volumes=volumes,
                name=volume_service_name,
                ports=['22/tcp'],
                image_builder=PrebuiltImageBuilder('ribozz/rsync')
            )
            self.services[volume_service_name] = volume_service
