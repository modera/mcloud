import json
import logging
import time
import sys
import inject
from mfcloud.tasks import TaskService
from mfcloud.txdocker import IDockerClient, DockerTwistedClient
import os
from twisted.internet import defer, reactor
from twisted.web import xmlrpc, server
import txredisapi
from txzmq import ZmqFactory, ZmqEndpoint, ZmqPubConnection


logger = logging.getLogger('mfcloud.server')

class ApiRpcServer(xmlrpc.XMLRPC):
    redis = inject.attr(txredisapi.Connection)
    zmq = inject.attr(ZmqPubConnection)

    def __init__(self, allowNone=False, useDateTime=False):
        xmlrpc.XMLRPC.__init__(self, allowNone, useDateTime)

        self.tasks = {}

    def task_completed(self, result, ticket_id):
        self.zmq.publish(json.dumps(result), 'task-completed-%s' % ticket_id)

        #print 'Result is %s' % result
        return defer.DeferredList([
            self.redis.set('mfcloud-ticket-%s-completed' % ticket_id, 1),
            self.redis.set('mfcloud-ticket-%s-result' % ticket_id, json.dumps(result))
        ])

    def task_failed(self, error, ticket_id):
        print 'Failure: <%s> %s' % (error.type, error.getErrorMessage())
        print error.printTraceback()
        self.zmq.publish("Failed: <%s> %s" % (error.type, error.getErrorMessage()), 'task-failed-%s' % ticket_id)

    def xmlrpc_task_start(self, task_name, *args, **kwargs):
        """
        Return all passed args.
        """

        d = self.redis.incr('mfcloud-ticket-id')

        def process_task_id(ticket_id):
            if not task_name in self.tasks:
                raise ValueError('No such task: %s' % task_name)
            task_defered = self.tasks[task_name](ticket_id, *args, **kwargs)

            task_defered.addCallback(self.task_completed, ticket_id)
            task_defered.addErrback(self.task_failed, ticket_id)

            return {
                'ticket_id': ticket_id
            }

        def on_error(error):
            return xmlrpc.Fault(1, "Task execution failed: <%s> %s" % (error.type, error.getErrorMessage()))

        d.addCallback(process_task_id)
        d.addErrback(on_error)

        return d

    def xmlrpc_is_completed(self, ticket_id):
        d = self.redis.get('mfcloud-ticket-%s-completed' % ticket_id)

        def on_result(result):
            return result == 1

        d.addCallback(on_result)
        return d

    def xmlrpc_get_result(self, ticket_id):
        d = self.redis.get('mfcloud-ticket-%s-result' % ticket_id)
        d.addCallback(lambda result: json.loads(result))
        return d



if __name__ == '__main__':

    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(logging.Formatter())
    console_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG)
    root_logger.debug('Logger initialized')

    def run_server(redis):

        zf = ZmqFactory()
        e = ZmqEndpoint('bind', 'tcp://127.0.0.1:5555')
        s = ZmqPubConnection(zf, e)

        def my_config(binder):
            binder.bind(txredisapi.Connection, redis)
            binder.bind(ZmqPubConnection, s)
            binder.bind(IDockerClient, DockerTwistedClient())

        # Configure a shared injector.
        inject.configure(my_config)

        tasks = TaskService()

        api = ApiRpcServer()
        tasks.register(api)

        reactor.listenTCP(7080, server.Site(api))

    txredisapi.Connection(dbid=1).addCallback(run_server)

    reactor.run()
