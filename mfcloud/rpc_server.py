import json
import inject
from twisted.internet import defer
from twisted.web import xmlrpc, server
import txredisapi


class ApiRpcServer(xmlrpc.XMLRPC):

    redis = inject.attr(txredisapi.Connection)

    def __init__(self, allowNone=False, useDateTime=False):
        xmlrpc.XMLRPC.__init__(self, allowNone, useDateTime)

        self.tasks = {}

    def task_completed(self, result, ticket_id):

        #print 'Result is %s' % result
        return defer.DeferredList([
            self.redis.set('mfcloud-ticket-%s-completed' % ticket_id, 1),
            self.redis.set('mfcloud-ticket-%s-result' % ticket_id, json.dumps(result))
        ])

    def xmlrpc_task_start(self, task_name, *args, **kwargs):
        """
        Return all passed args.
        """

        d = self.redis.incr('mfcloud-ticket-id')

        def process_task_id(ticket_id):
            task_defered = self.tasks[task_name](ticket_id, *args, **kwargs)

            task_defered.addCallback(self.task_completed, ticket_id)

            return {
                'ticket_id': ticket_id
            }

        d.addCallback(process_task_id)

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