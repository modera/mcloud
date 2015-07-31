
from fabric.context_managers import lcd, settings
from fabric.operations import local, run
from fabric.state import env

from mcloud.version import version
import os

env.hosts = ['root@dev1.cloud.modera.org']

def publish_plugin(name=None):
    with lcd('plugins/%s' % name):
        local('python setup.py sdist register upload')

def publish(type='patch'):
    local('bumpversion %s' % type)
    local('python setup.py sdist register upload')

    for plugin_name in [f for f in os.listdir('plugins') if os.path.isdir('plugins/%s' % f) and f != 'tpl']:
        print 'Publishing %s' % plugin_name
        with lcd('plugins/%s' % plugin_name):
            local('python setup.py sdist register upload')
            local('pip install -e .')

    local('git push')
    local('git push --tags')
    local('pip install -e .')



def new_plugin(name):
    os.chdir('plugins')
    cookiecutter('tpl', no_input=True, extra_context={
        'name': name,
        'version': version
    })

def docs():
    with lcd('docs/source/themes/cloud.modera.org'):
        local('git add .')
        with settings(warn_only=True):
            local('git commit')
            local('git push')

    local('git add docs/source/themes/cloud.modera.org')
    local('git add docs')
    local('git commit')
    local('git push')


def deploy_dev1():
    # publish()
    run('/opt/mcloud/bin/pip install mcloud -U')
    run('/opt/mcloud/bin/pip install mcloud-plugin-haproxy -U')
    run('service mcloud restart')
