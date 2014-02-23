from ficloud.fig_ext import transform_config


def test_transform_config():
    config = {'redis': {'image': 'orchardup/redis'},
              'web': {'build': '.',
                      'links': ['redis'],
                      'volumes': ['.:/code'],
                      '~dev': {'ports': ['5000:6000']},
                      '~prod': {'ports': ['5000:5000']}}}

    assert {'redis': {'image': 'orchardup/redis'},
            'web': {'build': '.',
                    'links': ['redis'],
                    'volumes': ['.:/code'],
                    'ports': ['5000:6000']}} == transform_config(config, env='dev')

    assert {'redis': {'image': 'orchardup/redis'},
            'web': {'build': '.',
                    'links': ['redis'],
                    'volumes': ['.:/code'],
                    'ports': ['5000:5000']}} == transform_config(config, env='prod')


def test_transform_config_root_level():
    config = {
        'foo': [123],
        '~1': {
            'hoho': 'hoho'
        },
        '~2': {
            'baz': 'baz'
        }
    }

    assert {
        'foo': [123],
        'hoho': 'hoho'
    } == transform_config(config, env='1')

    assert {
        'foo': [123],
        'baz': 'baz'
    } == transform_config(config, env='2')


def test_transform_config_default():
    config = {
        'foo': [123],
        '~dev': {
            'hoho': 'hoho'
        },
        '~2': {
            'baz': 'baz'
        }
    }

    assert {
        'foo': [123]
    } == transform_config(config)
