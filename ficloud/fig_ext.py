import errno
import logging
import pprint
import yaml
from fig.cli.main import TopLevelCommand
from fig.cli.utils import cached_property
from fig.project import Project
import os

log = logging.getLogger(__name__)


def transform_config(config, env=None):

    if isinstance(config, dict):
        obj = {}
        for key, val in config.items():
            if isinstance(key, str):
                if key[0] == '~':
                    if key[1:] == env:
                        obj.update(val)
                else:
                    obj[key] = transform_config(val, env)
        return obj
    elif isinstance(config, list):
        return map(lambda item: transform_config(item, env), config)
    else:
        return config


class FigCommand(TopLevelCommand):

    def __init__(self, env_name):
        # copy help from parent class
        self.__doc__ = TopLevelCommand.__doc__

        self.env_name = env_name

        super(FigCommand, self).__init__()

    @cached_property
    def project(self):
        try:
            yaml_path = self.check_yaml_filename()
            config = yaml.load(open(yaml_path))

            config = transform_config(config, env=self.env_name)

            print repr(config)

            return Project.from_config(self.project_name, config, self.client)

        except IOError as e:
            if e.errno == errno.ENOENT:
                log.error("Can't find %s. Are you in the right directory?", os.path.basename(e.filename))
            else:
                log.error(e)

            exit(1)
