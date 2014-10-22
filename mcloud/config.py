from collections import OrderedDict
from copy import deepcopy
import json
import collections
from abc import abstractmethod
from mcloud.container import PrebuiltImageBuilder, DockerfileImageBuilder
from mcloud.util import Interface
import os
from os.path import dirname
import yaml
from .service import Service
from voluptuous import Schema, MultipleInvalid
from voluptuous import Required
from twisted.python import log

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

    def __init__(self, file=None, source=None, app_name=None, path=None):

        if not file is None:
            if not os.path.exists(str(file)):
                raise ValueError('Bad config file given!')

            self._file = str(file)
            self._source = None

        elif not source is None:
            self._source = source
            self._file = None

        self.app_name = app_name
        self.path = path
        self.services = OrderedDict()

        self.config = None

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

    def load(self, process=True):

        try:
            if not self._file is None:
                with open(self._file) as f:
                    cfg = yaml.load(f, OrderedDictYAMLLoader)
            else:
                cfg = json.JSONDecoder(object_pairs_hook=collections.OrderedDict).decode(self._source)

            path = self.path

            self.prepare(config=cfg)

            self.validate(config=cfg)

            if process:
                self.process(config=cfg, path=path, app_name=self.app_name)

            self.config = cfg

        except ValueError as e:
            if self._file:
                raise ConfigParseError('Failed to parse %s: %s' % (self._file, e.message))
            else:
                raise ConfigParseError('Failed to parse source: %s' % e.message)

    def export(self):
        return json.dumps(self.config)

    def prepare(self, config):
        """
        Apply preprocessing to yaml config

        :param config:
        :return:
        """

        for service, cfg in config.items():
            if 'extend' in cfg:
                new_config = deepcopy(config[cfg['extend']])
                new_config.update(cfg)
                del new_config['extend']

                config[service] = new_config

    def validate(self, config):
        try:
            Schema({
                Required(basestring): {
                    'wait': int,
                    'image': basestring,
                    'build': basestring,

                    'volumes': {
                        basestring: basestring
                    },

                    'env': {
                        basestring: basestring
                    },

                    'cmd': basestring

                }
            })(config)

            for service in config.values():
                if not 'image' in service and not 'build' in service:
                    raise ValueError('You should define "image" or "build" as a vay to build a container.')
        except MultipleInvalid as e:
            raise ValueError(e)

        return True

    def process_command_build(self, service, config, path):

        if 'wait' in config:
            service.wait = config['wait']

        if 'cmd' in config and config['cmd'] and  len(str(config['cmd']).strip()) > 0:
            service.command = str(config['cmd']).strip()

    def process_volumes_build(self, service, config, path):
        service.volumes = []

        if 'volumes' in config and len(config['volumes']):

            if not os.path.exists(path):
                # log.msg('Base volumes directory do not exist: %s' % path)
                return
                # raise ValueError()

            path_real = os.path.realpath(path)
            if not path_real.endswith('/'):
                path_real += '/'

            if path is None:
                service.status_message += '\nService %s requested to attach volumes, but ' \
                                          'yaml config was uploaded separately ' \
                                          'without source files attached.'
                return

            for local_path, container_path in config['volumes'].items():

                if local_path.startswith('~'):
                    # log.msg('You can not mount directories outside of project directory: %s -> %s' % (path, local_path))
                    # raise ValueError('')
                    continue

                path_join = os.path.realpath(os.path.join(path, local_path))

                if not path_join.startswith(path_real):
                    continue
                    # log.msg('You can not mount directories outside of project directory: %s -> %s' % (path, path_real))

                service.volumes.append({
                    'local': path_join,
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

            # expose mcloud api
            s.volumes.append({'local': '/var/run/mcloud', 'remote': '/var/run/mcloud'})
            s.volumes.append({'local': dirname(__file__) + '/api.py', 'remote': '/usr/bin/@me'})

            self.services[name] = s
