from flexmock import flexmock
from mfcloud.application import ApplicationController, Application
from mfcloud.config import YamlConfig
from mfcloud.deployment import DeploymentController, Deployment
from mfcloud.tasks import TaskService
from mfcloud.util import inject_services
import pytest
from twisted.internet import defer
import txredisapi


@pytest.inlineCallbacks
def test_init_app_task():

    ac = flexmock()

    def configure(binder):
        binder.bind(ApplicationController, ac)

    with inject_services(configure):

        ac.should_receive('create').with_args('foo', {'path': 'some/path'}).and_return(defer.succeed(flexmock()))

        ts = TaskService()

        r = yield ts.task_init_app(123123, 'foo', 'some/path')
        assert r is True


@pytest.inlineCallbacks
def test_init_app_task_source():

    ac = flexmock()

    def configure(binder):
        binder.bind(ApplicationController, ac)

    with inject_services(configure):

        ac.should_receive('create').with_args('foo', {'source': 'foo: bar'}).and_return(defer.succeed(flexmock()))

        ts = TaskService()

        r = yield ts.task_init_app_source(123123, 'foo', 'foo: bar')
        assert r is True


@pytest.inlineCallbacks
def test_list_app_task():

    ac = flexmock()

    def configure(binder):
        binder.bind(ApplicationController, ac)

    with inject_services(configure):

        ac.should_receive('list').and_return(defer.succeed({'foo': Application({'path': 'some/path'})}))

        ts = TaskService()

        r = yield ts.task_list_app(123123)
        assert r == [('foo', 'some/path')]




@pytest.inlineCallbacks
def test_list_deployments_task():

    ac = flexmock()
    dc = flexmock()

    def configure(binder):
        binder.bind(ApplicationController, ac)
        binder.bind(DeploymentController, dc)

    with inject_services(configure):

        ac.should_receive('get').with_args('foo').and_return(defer.succeed(Application({'path': 'some/path'})))
        dc.should_receive('list').and_return(defer.succeed([Deployment(public_domain='foo.bar', name='baz', apps=['foo'])]))

        ts = TaskService()

        r = yield ts.task_list_deployments(123123)


        assert r == [{
            'name': 'baz',
            'public_domain': 'foo.bar',
            'apps': [
                {
                    'name': 'foo',
                    'path': 'some/path'
                }
            ]
        }]




@pytest.inlineCallbacks
def test_expand_app_list_on_deployment():

    ac = flexmock()
    dc = flexmock()

    def configure(binder):
        binder.bind(ApplicationController, ac)

    with inject_services(configure):

        ac.should_receive('get').with_args('foo').and_return(defer.succeed(Application({'path': 'some/path'})))
        ac.should_receive('get').with_args('boo').and_return(defer.succeed(Application({'path': 'some/other/path'})))

        ts = TaskService()

        r = yield ts.expand_app_list_on_deployment({
            'apps': ['foo', 'boo']
        })


        assert r == {
            'apps': [
                {
                    'name': 'foo',
                    'path': 'some/path'
                },
                {
                    'name': 'boo',
                    'path': 'some/other/path'
                }
            ]
        }
