from flexmock import flexmock
from mfcloud.application import ApplicationController, Application
from mfcloud.config import YamlConfig
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

        ac.should_receive('create').with_args('foo', 'some/path').and_return(defer.succeed(flexmock()))

        ts = TaskService()

        r = yield ts.task_init_app('foo', 'some/path')
        assert r is True

@pytest.inlineCallbacks
def test_list_app_task():

    ac = flexmock()

    def configure(binder):
        binder.bind(ApplicationController, ac)

    with inject_services(configure):

        ac.should_receive('list').and_return(defer.succeed({'foo': Application({'path': 'some/path'})}))

        ts = TaskService()

        r = yield ts.task_list_app()
        assert r == [('foo', 'some/path')]
