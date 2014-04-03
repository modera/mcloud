from mfcloud.api import LocalDeploymentEndpoint
from mfcloud.config import IConfig


def test_load_config(tmpdir):
    p = tmpdir.mkdir('boo_app')
    p = p.join('mfcloud.yml')
    p.write("""
foo:
    image: bar/baz
""")

    l = LocalDeploymentEndpoint(path='%s/boo_app' % str(tmpdir))

    assert l.list_applications() == ['boo_app']
    assert l.list_application_versions('boo_app') == ['dev']

    config = l.load_application_version_config('boo_app', 'dev')

    assert isinstance(config, IConfig)

    assert config.get_services().keys() == ['foo']

