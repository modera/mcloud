from flexmock import flexmock
from mcloud.application import ApplicationController, Application
from mcloud.deployment import DeploymentController, Deployment
from mcloud.tasks import TaskService
from mcloud.util import inject_services, injector, txtimeout
import pytest
from twisted.internet import defer, reactor
import txredisapi


@pytest.mark.xfail
def test_tasks_are_registered():

    with injector({}):

        ts = TaskService()
        tasks = ts.collect_tasks()

        assert tasks['help'] == ts.task_help



@pytest.inlineCallbacks
def test_init_app_task():

    ac = flexmock()

    def configure(binder):
        binder.bind(ApplicationController, ac)

    with inject_services(configure):

        ac.should_receive('create').with_args('foo', {'path': 'some/path'}).and_return(defer.succeed(flexmock()))
        ac.should_receive('list').and_return(defer.succeed('result-of-list-operation'))

        ts = TaskService()

        r = yield ts.task_init(123123, 'foo', 'some/path')
        assert r == 'result-of-list-operation'


@pytest.inlineCallbacks
def test_init_app_task_source():

    ac = flexmock()

    def configure(binder):
        binder.bind(ApplicationController, ac)

    with inject_services(configure):

        ac.should_receive('create').with_args('foo', {'source': 'foo: bar'}).and_return(defer.succeed(flexmock())).once()
        ac.should_receive('list').and_return(defer.succeed('result-of-list-operation'))

        ts = TaskService()

        r = yield ts.task_init_source(123123, 'foo', 'foo: bar')
        assert r == 'result-of-list-operation'

@pytest.inlineCallbacks
@pytest.mark.xfail
def test_deployment_new_app_task_source():

    dc = flexmock()

    def configure(binder):
        binder.bind(DeploymentController, dc)

    with inject_services(configure):

        dc.should_receive('new_app').with_args('baz', 'foo', {'source': 'foo: bar'}).and_return(defer.succeed(flexmock())).once()

        ts = TaskService()

        r = yield ts.task_deployment_new_app_source(123123, 'baz', 'foo', 'foo: bar')
        assert r is True


@pytest.inlineCallbacks
def test_list_app_task():

    ac = flexmock()

    ac.should_receive('list').and_return(defer.succeed(['foo', 'bar'])).once()

    def configure(binder):
        binder.bind(ApplicationController, ac)

    with inject_services(configure):



        ts = TaskService()

        r = yield ts.task_list(123123)
        assert r == ['foo', 'bar']


@pytest.inlineCallbacks
def test_push_task():

    ac = flexmock()

    ac.should_receive('list').and_return(defer.succeed(['foo', 'bar'])).once()

    def configure(binder):
        binder.bind(ApplicationController, ac)

    with inject_services(configure):

        ts = TaskService()

        r = yield ts.task_list(123123)
        assert r == ['foo', 'bar']


@pytest.inlineCallbacks
@pytest.mark.xfail
def test_register_file():

    rc = yield txredisapi.Connection(dbid=2)
    yield rc.flushdb()

    def configure(binder):
        binder.bind(txredisapi.Connection, rc)

    with inject_services(configure):

        ts = TaskService()

        r = yield ts.task_register_file(None)
        assert r == 1

        r = yield ts.task_register_file(None)
        assert r == 2

        r = yield ts.task_register_file(None)
        assert r == 3





@pytest.inlineCallbacks
@pytest.mark.xfail
def test_list_deployments_task():

    ac = flexmock()
    dc = flexmock()

    def configure(binder):
        binder.bind(ApplicationController, ac)
        binder.bind(DeploymentController, dc)

    with inject_services(configure):

        ac.should_receive('get').with_args('foo').and_return(defer.succeed(Application({'path': 'some/path'}))).once()
        dc.should_receive('list').and_return(defer.succeed([Deployment(public_domain='foo.bar', name='baz', apps=['foo'])])).once()

        ts = TaskService()

        r = yield ts.task_deployments(123123)


        assert r == [{
            'name': 'baz',
            'public_domain': 'foo.bar',
            'apps': [
                {
                    'name': 'foo',
                    'config': {'path': 'some/path'}
                }
            ]
        }]

@pytest.inlineCallbacks
def test_set_var_task():

    def timeout():
        print('Can not connect to redis!')
        reactor.stop()

    redis = yield txtimeout(txredisapi.Connection(dbid=2), 2, timeout)
    yield redis.flushdb()

    def configure(binder):
        binder.bind(txredisapi.Connection, redis)

    with inject_services(configure):

        ts = TaskService()

        r = yield ts.task_list_vars(123123)
        assert r == {}

        r = yield ts.task_set_var(123123, 'boo', '123')
        assert r == {'boo': 123}

        r = yield ts.task_list_vars(123123)
        assert r == {'boo': 123}

        r = yield ts.task_set_var(123123, 'boo2', '1234')
        assert r == {'boo': 123, 'boo2': 1234}

        r = yield ts.task_rm_var(123123, 'boo')
        assert r == {'boo2': 1234}