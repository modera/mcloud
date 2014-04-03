import os
from os.path import dirname
import yaml
from .service import Service


class PrebuiltImageBuilder(object):
    def __init__(self, image):
        super(PrebuiltImageBuilder, self).__init__()

        self.image = image


class DockerfileImageBuilder(object):
    def __init__(self, path):
        super(DockerfileImageBuilder, self).__init__()
        self.path = path


class YamlConfig(object):

    def __init__(self, file=None):
        super(YamlConfig, self).__init__()

        if not file is None and not os.path.exists(str(file)):
            raise ValueError('Bad config file given!')

        self._file = str(file)

        self.services = []


    def load(self):

        with open(self._file) as f:
            print f
            cfg = yaml.load(f)
            self.process(config=cfg, path=dirname(self._file))

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

            self.services.append(s)
