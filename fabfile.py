from fabric.context_managers import lcd
from fabric.operations import local, os

from cookiecutter.main import cookiecutter
from mcloud.version import version


def publish(type='patch'):
    local('bumpversion %s' % type)
    local('python setup.py sdist register upload')

    for plugin_name in [f for f in os.listdir('plugins') if os.path.isdir('plugins/%s' % f) and f != 'tpl']:
        print 'Publishing %s' % plugin_name
        with lcd('plugins/%s' % plugin_name):
            local('python setup.py sdist register upload')

    local('git push')
    local('git push --tags')


def new_plugin(name):
    os.chdir('plugins')
    cookiecutter('tpl', no_input=True, extra_context={
        'name': name,
        'version': version
    })