import json
import os
from prettytable import PrettyTable
from twisted.internet import defer, reactor
from twisted.web.xmlrpc import Proxy
from txzmq import ZmqFactory, ZmqEndpoint, ZmqSubConnection


class ApiRpcClient(object):

    def _remote_exec(self, task_name, on_result, *args):

        ticket = {}

        zf2 = ZmqFactory()
        e2 = ZmqEndpoint('connect', 'tcp://127.0.0.1:5555')

        s2 = ZmqSubConnection(zf2, e2)
        s2.subscribe("")

        def doPrint(message, tag):
            # print "message received: <%s> %s" % (tag, message)

            if tag == 'task-completed-%s' % ticket['ticket_id']:
                reactor.stop()

                data = json.loads(message)
                if isinstance(data, dict) and 'message' in data:
                    print data['message']
                else:
                    on_result(data)


            elif tag == 'task-failed-%s' % ticket['ticket_id']:
                reactor.stop()
                print 'Task failed during execution: %s' % message


            elif tag == 'log-%s' % ticket['ticket_id']:
                data = json.loads(message)
                print(data)

        s2.gotMessage = doPrint


        proxy = Proxy('http://127.0.0.1:7080')
        d = proxy.callRemote('task_start', task_name, *args)

        def ready(result):
            print result
            ticket['ticket_id'] = result['ticket_id']

        def failed(result):
            print('Failed to execute the task: %s' % result.getErrorMessage())
            reactor.stop()

        d.addCallback(ready)
        d.addErrback(failed)
        reactor.run()

    def init(self, name, path, **kwargs):

        def on_result(data):
            print 'result: %r' % data

        self._remote_exec('init', on_result, name, os.path.realpath(path))

    def list(self, **kwargs):

        def on_result(data):

            x = PrettyTable(["Application name", "Application path"])
            for row in data:
                x.add_row(row)
                print x

        self._remote_exec('list', on_result)

    def status(self, name, **kwargs):

        def on_result(data):

            print 'Services:'

            x = PrettyTable(["Service name", "is created", "is running"])
            for row in data:
                x.add_row(row)
                print x

        self._remote_exec('status', on_result, name)

    def remove(self, name, **kwargs):

        def on_result(data):
            print 'result: %r' % data

        self._remote_exec('remove', on_result, name)


def populate_client_parser(subparsers):


    cmd = subparsers.add_parser('init', help='Creates a new application')
    cmd.add_argument('name', help='App name')
    cmd.add_argument('path', help='Path', nargs='?', default='.')
    cmd.set_defaults(func='init')

    cmd = subparsers.add_parser('list', help='List registered applications')
    cmd.set_defaults(func='list')

    cmd = subparsers.add_parser('remove', help='Remove application')
    cmd.add_argument('name', help='App name')
    cmd.set_defaults(func='remove')

    cmd = subparsers.add_parser('status', help='Remove application')
    cmd.add_argument('name', help='App name')
    cmd.set_defaults(func='status')


    # # # mfcloud use ubuntu@myserver.com
    # fig_cmd = subparsers.add_parser('fig', help='Executes fig commands')
    # fig_cmd.add_argument('--env', help='Environment name', default='dev')
    # fig_cmd.add_argument('--app-name', help='App name')
    # fig_cmd.add_argument('fig_cmd', help='Fig command to execeute')
    # fig_cmd.set_defaults(func=func=fig_main)


    # cmd = subparsers.add_parser('start', help='Run services as daemons')
    # cmd.add_argument('services', help='Service names', nargs='*')
    # cmd.add_argument('--no-logs', dest='logs', action='store_false', default=True, help='No logs')
    # cmd.add_argument('--rebuild', action='store_true', default=False, help='Rebuild container')
    # cmd.set_defaults(func='start')

    # cmd = subparsers.add_parser('run', help='Run command on a service')
    # cmd.add_argument('service', help='Service name')
    # cmd.add_argument('command', help='Command to run')
    # cmd.add_argument('--no-tty', dest='disable_tty', action='store_true', default=False, help='No tty')
    # cmd.set_defaults(func='run')
    #
    # cmd = subparsers.add_parser('stop', help='Stop services')
    # cmd.add_argument('services', help='Service names', nargs='*')
    # cmd.set_defaults(func='stop')
    #
    # cmd = subparsers.add_parser('destroy', help='Destory services and containers')
    # cmd.add_argument('services', help='Service names', nargs='*')
    # cmd.set_defaults(func='destroy')
    #
    # cmd = subparsers.add_parser('rebuild', help='Destory services and containers')
    # cmd.add_argument('services', help='Service names', nargs='*')
    # cmd.set_defaults(func='rebuild')
    #
    # cmd = subparsers.add_parser('logs', help='Fetch logs from containers')
    # cmd.add_argument('services', help='Service names', nargs='*')
    # cmd.set_defaults(func='logs')


    # 'PS1=(.env)\[\e]0;\u@\h: \w\a\]${debian_chroot:+($debian_chroot)}\u@\h:\w\$'


    # cmd = subparsers.add_parser('volumes', help='Show volumes of current project')
    # cmd.add_argument('services', help='Service names', nargs='*')
    # cmd.add_argument('--json', action='store_true', default=False)
    # cmd.set_defaults(func='list_volumes')
    #
    # cmd = subparsers.add_parser('volume-push', help='Push volume to remote server')
    # cmd.add_argument('volumes', help='Volume specs', nargs='*')
    # cmd.set_defaults(func='push_volumes')
    #
    # cmd = subparsers.add_parser('volume-pull', help='Push volume to remote server')
    # cmd.add_argument('volumes', help='Volume specs', nargs='*')
    # cmd.set_defaults(func='pull_volumes')

    # cmd = subparsers.add_parser('status', help='Show current status of services')
    # cmd.set_defaults(func='status')



