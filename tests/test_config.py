from collections import OrderedDict
from flexmock import flexmock
from mcloud.config import YamlConfig, Service, UnknownServiceError, ConfigParseError
from mcloud.container import PrebuiltImageBuilder, DockerfileImageBuilder
import pytest


def test_not_existent_file():
    with pytest.raises(ValueError):
        YamlConfig(file='Not existent path')


def test_none_to_parser():
    YamlConfig()


def test_load_config_prepare(tmpdir):
    config = {
        'foo': {
            'image': 'foo',
            'env': {
                'bar': 'baz'
            },
            'cmd': 'some'
        },

        'bar': {
            'extend': 'foo',
            'cmd': 'other'
        }
    }

    yc = YamlConfig()

    yc.prepare(config)

    assert config['bar'] == {
        'image': 'foo',
        'env': {
            'bar': 'baz'
        },
        'cmd': 'other'
    }


def test_load_config(tmpdir):
    p = tmpdir.join('mcloud.yml')
    p.write('foo: bar')

    config = YamlConfig(file=p.realpath(), app_name='myapp')

    flexmock(config).should_receive('prepare').with_args({'foo': 'bar'}).once()
    flexmock(config).should_receive('validate').with_args({'foo': 'bar'}).once()
    flexmock(config).should_receive('process').with_args({'foo': 'bar'}, path=p.dirname, app_name='myapp').once()
    config.load()


def test_load_config_from_config():
    config = YamlConfig(source='foo: bar', app_name='myapp')

    flexmock(config).should_receive('prepare').with_args({'foo': 'bar'}).once()
    flexmock(config).should_receive('validate').with_args({'foo': 'bar'}).once()
    flexmock(config).should_receive('process').with_args({'foo': 'bar'}, path=None, app_name='myapp').once()
    config.load()


def test_load_config_not_valid(tmpdir):
    p = tmpdir.join('mcloud.yml')
    p.write('foo: bar')

    config = YamlConfig(file=p.realpath(), app_name='myapp')

    flexmock(config).should_receive('prepare').with_args({'foo': 'bar'}).once()
    flexmock(config).should_receive('validate').with_args({'foo': 'bar'}).once().and_raise(ValueError('boo'))
    flexmock(config).should_receive('process').times(0)

    with pytest.raises(ConfigParseError):
        config.load()


@pytest.mark.parametrize("config", [

    # one service - image
    {
        'foo': {
            'image': 'boo'
        }
    },

    # one service - build
    {
        'foo': {
            'build': 'boo'
        }
    },

    # one service - full config
    {
        'foo': {
            'image': 'boo',
            'env': {
                'boo': 'baz',
                'boo2': 'baz',
                'boo3': 'baz',
            },

            'volumes': {
                'foo1': 'bar1',
                'foo2': 'bar2',
                'foo3': 'bar3',
            }

        }
    }
])
def test_validate_valid(config):
    c = YamlConfig()
    assert c.validate(config)

def test_validate_ordered_dict():
    c = YamlConfig()
    config = OrderedDict([('web', OrderedDict([('image', 'orchardup/nginx'), ('volumes', OrderedDict([('public', '/var/www')]))]))])
    assert c.validate(config)


@pytest.mark.parametrize("config", [

    # no services
    {},

    # no image or build
    {'foo': {}},

    # some random key
    {
        'foo': {
            'build1': 'boo'
        }
    }
])
def test_validate_invalid(config):
    c = YamlConfig()

    with pytest.raises(ValueError):
        assert c.validate(config)


def test_process():
    c = YamlConfig()

    flexmock(c)

    c.should_receive('process_image_build').once()
    c.should_receive('process_volumes_build').once()
    c.should_receive('process_command_build').once()

    c.process({
                  'nginx': {'foo': 'bar'}
              }, path='foo')

    assert isinstance(c.services['nginx'], Service)
    assert c.services['nginx'].name == 'nginx'


def test_process_with_app_name():
    c = YamlConfig()

    flexmock(c)

    c.should_receive('process_image_build').once()
    c.should_receive('process_volumes_build').once()
    c.should_receive('process_command_build').once()

    c.process({
                  'nginx': {'foo': 'bar'}
              }, path='foo', app_name='myapp')

    assert isinstance(c.services['nginx.myapp'], Service)
    assert c.services['nginx.myapp'].name == 'nginx.myapp'


def test_build_command_empty():
    s = Service()
    c = YamlConfig()

    c.process_command_build(s, {}, '/base/path')
    assert s.command == None


def test_build_command_none():
    s = Service()
    c = YamlConfig()

    c.process_command_build(s, {'cmd': None}, '/base/path')
    assert s.command == None


def test_build_command_empty_string():
    s = Service()
    c = YamlConfig()

    c.process_command_build(s, {'cmd': ''}, '/base/path')
    assert s.command == None


def test_build_command_ok():
    s = Service()
    c = YamlConfig()

    c.process_command_build(s, {'cmd': 'ok --some args'}, '/base/path')
    assert s.command == 'ok --some args'


def test_build_build_volumes_empty():
    s = Service()
    c = YamlConfig()

    c.process_volumes_build(s, {'volumes': []}, '/base/path')
    assert s.volumes == []


def test_build_build_volumes_none():
    s = Service()
    c = YamlConfig()

    c.process_volumes_build(s, {}, '/base/path')
    assert s.volumes == []


def test_build_build_volumes_several():
    s = Service()
    c = YamlConfig()

    c.process_volumes_build(s, {'volumes': {
        'foo1': 'bar1',
        'foo2': 'bar2',
        'foo3': 'bar3',
    }}, '/base/path')

    assert s.volumes == [
        {'local': '/base/path/foo1', 'remote': 'bar1'},
        {'local': '/base/path/foo2', 'remote': 'bar2'},
        {'local': '/base/path/foo3', 'remote': 'bar3'}
    ]


def test_build_build_env_empty():
    s = Service()
    c = YamlConfig()

    c.process_env_build(s, {'env': []}, '/base/path')
    assert s.env == {}


def test_build_build_env_none():
    s = Service()
    c = YamlConfig()

    c.process_env_build(s, {}, '/base/path')
    assert s.env == {}


def test_build_build_env_several():
    s = Service()
    c = YamlConfig()

    c.process_env_build(s, {'env': {
        'foo1': 'bar1',
        'foo2': 'bar2',
        'foo3': 'bar3',
    }}, '/base/path')

    assert s.env == {
        'foo1': 'bar1',
        'foo2': 'bar2',
        'foo3': 'bar3',
    }


def test_build_image_image():
    s = Service()
    c = YamlConfig()

    c.process_image_build(s, {'image': 'foo/bar'}, '/base/path')

    assert isinstance(s.image_builder, PrebuiltImageBuilder)
    assert s.image_builder.image == 'foo/bar'


def test_build_image_dockerfile():
    s = Service()
    c = YamlConfig()

    c.process_image_build(s, {'build': 'foo/bar'}, '/base/path')

    assert isinstance(s.image_builder, DockerfileImageBuilder)
    assert s.image_builder.path == '/base/path/foo/bar'


def test_build_image_dockerfile_no_path():
    s = Service()
    c = YamlConfig()

    with pytest.raises(ConfigParseError):
        c.process_image_build(s, {'build': 'foo/bar'}, None)


def test_build_image_empty():
    s = Service()
    c = YamlConfig()

    with pytest.raises(ValueError) as e:
        c.process_image_build(s, {}, '/base/path')


def test_get_service():
    c = YamlConfig()
    c.services = {'foo': 'bar'}
    assert c.get_service('foo') == 'bar'


def test_get_service_no():
    c = YamlConfig()
    c.services = {'foo': 'bar'}

    with pytest.raises(UnknownServiceError):
        c.get_service('baz')








