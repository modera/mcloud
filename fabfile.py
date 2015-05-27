from fabric.context_managers import lcd
from fabric.operations import local


def publish(type='patch'):
    local('bumpversion %s' % type)
    local('python setup.py sdist register upload')

    with lcd('plugins/haproxy'):
        local('python setup.py sdist register upload')

    local('git push')
    local('git push --tags')