"""Management utilities."""
from fabric.context_managers import cd, lcd

from fabric.contrib.console import confirm
from fabric.api import abort, env, local, settings, task
from fabric.operations import run


@task
def deploy():
    local('python setup.py sdist register upload')

    all_plugins = [
        'simple_publish',
        # 'haproxy',
    ]
    for plugin in all_plugins:
        with lcd('plugins/%s' % plugin):
            local('python setup.py sdist register upload')
