
from flexmock import flexmock
from mfcloud.config import YamlConfig, Service
from mfcloud.container import PrebuiltImageBuilder, DockerfileImageBuilder
import pytest


def test_not_existent_file():
    with pytest.raises(ValueError):
        YamlConfig(file='Not existent path')

def test_none_to_parser():
    YamlConfig()


def test_load_cofig(tmpdir):

    p = tmpdir.join('mfcloud.yml')
    p.write('foo: bar')

    config = YamlConfig(file=p.realpath())

    flexmock(config).should_receive('validate').with_args({'foo': 'bar'}).once()
    flexmock(config).should_receive('process').with_args({'foo': 'bar'}, path=p.dirname).once()
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


def test_build_image_empty():

    s = Service()
    c = YamlConfig() 

    with pytest.raises(ValueError) as e:
        c.process_image_build(s, {}, '/base/path')









