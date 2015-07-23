from collections import OrderedDict
import os
from flexmock import flexmock
from mcloud.config import YamlConfig, Service, UnknownServiceError, ConfigParseError
from mcloud.container import PrebuiltImageBuilder, DockerfileImageBuilder, InlineDockerfileImageBuilder
import pytest


def test_not_existent_file():
    with pytest.raises(ValueError):
        YamlConfig(file='Not existent path')


def test_none_to_parser():
    YamlConfig()


def test_load_config_prepare():
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

    processed = yc.prepare(config)

    assert processed['bar'] == {
        'image': 'foo',
        'env': {
            'bar': 'baz'
        },
        'cmd': 'other'
    }


def test_filter_env_non_dict():
    """
    pass through non-dict elements
    """
    yc = YamlConfig(env='xx')
    result = yc.filter_env('foo')
    assert result == 'foo'

def test_filter_env_dict_no_env():
    """
    pass through dict elements without ~
    """
    yc = YamlConfig(env='xx')
    flexmock(yc).should_call('filter_env').with_args({'foo': 'bar'}).once()
    flexmock(yc).should_call('filter_env').with_args('bar').once()
    result = yc.filter_env({'foo': 'bar'})

    assert result == {'foo': 'bar'}

def test_filter_env_remove():
    """
    ~xxx syntax: remove elements that not match
    """
    yc = YamlConfig(env='xx')
    result = yc.filter_env({
        '~foo': 'bar'
    })
    assert result == {}

def test_filter_env_non_dict_in_match():
    """
    ~xxx syntax: should contain dict
    """
    yc = YamlConfig(env='foo')

    with pytest.raises(TypeError):
        yc.filter_env({
            '~foo': 'bar'
        })

def test_filter_env_keep():
    """
    ~xxx syntax: keep elements that match
    """
    yc = YamlConfig(env='foo')
    flexmock(yc).should_call('filter_env').with_args({'~foo': {'bar': 'baz'}}).once().and_return({'bar': 'baz'})
    flexmock(yc).should_call('filter_env').with_args({'bar': 'baz'}).once().and_return({'bar': 'baz'})
    flexmock(yc).should_call('filter_env').with_args('baz').once().and_return('baz')
    result = yc.filter_env({
        '~foo': {'bar': 'baz'}
    })
    assert result == {'bar': 'baz'}


def test_load_config_prepare_env():
    yc = YamlConfig(env='myenv')

    flexmock(yc).should_receive('filter_env').with_args({'foo': {'bar': 'baz'}}).once().and_return({'fas': {'bar': 'baz'}})
    processed = yc.prepare({'foo': {'bar': 'baz'}})

    assert processed == {'fas': {'bar': 'baz'}}

def test_load_config(tmpdir):
    p = tmpdir.join('mcloud.yml')
    p.write('foo: bar')

    config = YamlConfig(file=p.realpath(), app_name='myapp')

    flexmock(config).should_receive('prepare').with_args({'foo': 'bar'}).once().and_return({'foo': 'bar1'})
    flexmock(config).should_receive('validate').with_args({'foo': 'bar1'}).once()
    flexmock(config).should_receive('process').with_args(OrderedDict([('foo', 'bar1')]), path=None, app_name='myapp', client='booo').once()
    config.load(client='booo')

def test_load_config_from_config():
    config = YamlConfig(source='{"foo": "bar"}', app_name='myapp')

    flexmock(config).should_receive('prepare').with_args({'foo': 'bar'}).once().and_return({'foo': 'bar1'})
    flexmock(config).should_receive('validate').with_args({'foo': 'bar1'}).once()
    flexmock(config).should_receive('process').with_args(OrderedDict([('foo', 'bar1')]), path=None, app_name='myapp', client='booo').once()
    config.load(client='booo')


def test_load_config_not_valid(tmpdir):
    p = tmpdir.join('mcloud.yml')
    p.write('foo: bar')

    config = YamlConfig(file=p.realpath(), app_name='myapp')

    flexmock(config).should_receive('prepare').with_args({'foo': 'bar'}).once().and_return({'foo': 'bar1'})
    flexmock(config).should_receive('validate').with_args({'foo': 'bar1'}).once().and_raise(ValueError('boo'))
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

        },
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


def test_process_with_local_config():
    c = YamlConfig(source='{"nginx": {"image": "bar"}, "---": {"commands": {"bar": ["foo"]}}}')

    flexmock(c)

    c.should_receive('process_local_config').once().with_args({"commands": {"bar": ["foo"]}})
    c.load(process=False)

def test_process_local_config_hosts():
    c = YamlConfig()
    c.process_local_config({'hosts': {'foo': 'bar'}})

    assert c.hosts == {'foo': 'bar'}

def test_process_local_config_commands():
    c = YamlConfig()
    c.process_local_config({'commands': {
        'push (Upload code to remove server)': ['sync . {host} --path ticcet/'],
        'pull': ['foo', 'bar']
    }})

    assert c.get_commands() == {
        'push': {
            'help': 'Upload code to remove server',
            'commands':  ['sync . {host} --path ticcet/']
        },
        'pull': {
            'help': 'pull command',
            'commands':  ['foo', 'bar']
        }
    }



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


def test_build_build_volumes_several(tmpdir):
    s = Service()
    c = YamlConfig()

    foo1 = tmpdir.mkdir('foo1')
    foo2 = tmpdir.mkdir('foo2')
    foo3 = tmpdir.mkdir('foo3')

    c.process_volumes_build(s, {'volumes': {
        'foo1': 'bar1',
        'foo2': 'bar2',
        'foo3': 'bar3',
    }}, str(tmpdir))

    assert s.volumes == [
        {'local': str(foo1), 'remote': 'bar1'},
        {'local': str(foo2), 'remote': 'bar2'},
        {'local': str(foo3), 'remote': 'bar3'}
    ]



def test_build_build_volumes_single_file(tmpdir):
    s = Service()
    c = YamlConfig()

    tmpdir.join('nginx.conf').write('foo')

    c.process_volumes_build(s, {'volumes': {
        'nginx.conf': 'bar1',
    }}, str(tmpdir))

    assert s.volumes == [
        {'local': str(tmpdir.join('nginx.conf')), 'remote': 'bar1'},
    ]

def test_build_build_volumes_basepath(tmpdir):
    s = Service()
    c = YamlConfig()

    c.process_volumes_build(s, {'volumes': {
        '.': 'bar1',
    }}, str(tmpdir))

    assert s.volumes == [
        {'local': str(tmpdir), 'remote': 'bar1'},
    ]



@pytest.mark.parametrize("path,result", [
    ('/root', '/foo/root'),
    ('.', '/foo'),
    ('../', '/foo'),
    ('../bar/baz/../', '/foo/bar'),
    ('./././../', '/foo'),
    ('././some/crazy/something/../../..//../../../../../../../', '/foo'),
    ('~/', '/foo')
])
def test_build_build_volumes_hackish_paths(path, result):
    s = Service()
    c = YamlConfig()

    c.process_volumes_build(s, {'volumes': {
        path: 'bar',
    }}, '/foo')

    assert s.volumes == [
        {'local': result, 'remote': 'bar'},
    ]


def test_build_build_env_empty():
    s = Service()
    c = YamlConfig()

    c.process_env_build(s, {'env': []}, '/base/path')
    assert s.env == {}


def test_build_build_env_none():
    s = Service()
    c = YamlConfig(env='dev')

    c.process_env_build(s, {}, '/base/path')
    assert s.env == {'env': 'dev'}


def test_build_build_env_several():
    s = Service()
    c = YamlConfig(env='prod')

    c.process_env_build(s, {'env': {
        'foo1': 'bar1',
        'foo2': 'bar2',
        'foo3': 'bar3',
    }}, '/base/path')

    assert s.env == {
        'env': 'prod',
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

def test_build_inline_dockerfile():
    s = Service()
    c = YamlConfig()

    c.process_image_build(s, {'dockerfile': 'FROM foo\nWORKDIR boo'}, '/base/path')

    assert isinstance(s.image_builder, InlineDockerfileImageBuilder)
    assert s.image_builder.files['Dockerfile'] == 'FROM foo\nWORKDIR boo'


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



def test_hosts_config():
    c = YamlConfig()
    c.hosts = OrderedDict((
        ('boo', 'app@somehost.com'),
        ('foo', 'app@other.com')
    ))

    assert c.get_command_host() == 'app@somehost.com'
    assert c.get_command_host('boo') == 'app@somehost.com'
    assert c.get_command_host('foo') == 'app@other.com'
