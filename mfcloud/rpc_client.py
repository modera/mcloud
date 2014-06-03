import json
import logging
import sys
from mfcloud.config import ConfigParseError
import os
import pprintpp
from prettytable import PrettyTable, FRAME, ALL
from texttable import Texttable
from twisted.internet import defer, reactor
from twisted.internet.error import ConnectionRefusedError
from twisted.web.xmlrpc import Proxy
from txzmq import ZmqFactory, ZmqEndpoint, ZmqSubConnection


logger = logging.getLogger('mfcloud.client')

class ApiRpcClient(object):

    def __init__(self):
        super(ApiRpcClient, self).__init__()

        self.init_zmq()

        self.ticket = {}
        self.proxy = Proxy('http://127.0.0.1:7080')

        self.reactor = reactor

    def on_result(self, result):
        pass

    def init_zmq(self):
        zf2 = ZmqFactory()
        e2 = ZmqEndpoint('connect', 'tcp://127.0.0.1:5555')
        s2 = ZmqSubConnection(zf2, e2)
        s2.subscribe("")
        s2.gotMessage = self._on_message

    def _remote_exec(self, task_name, on_result, *args):

        self.on_result = on_result

        logger.debug('rpc call: task_start %s %s' % (task_name, args))
        d = self.proxy.callRemote('task_start', task_name, *args)

        def ready(result):
            logger.debug('rpc response:%s' % result)
            self.ticket['ticket_id'] = result['ticket_id']

        def failed(failure):

            if failure.type == ConnectionRefusedError:
                print('\nConnection failure. Server is not started? \n\nRun "mfcloud service start"\n')
            else:
                print('Failed to execute the task: %s' % failure.getErrorMessage())
            self.reactor.stop()

        d.addCallback(ready)
        d.addErrback(failed)
        self.reactor.run()

    def _task_failed(self, message):
        self.reactor.stop()
        print message

    def _task_completed(self, message):
        self.reactor.stop()
        data = json.loads(message)
        self.on_result(data)

    def _on_message(self, message, tag):

        logger.debug('zmq message: %s tag: %s', message, tag)

        if not 'ticket_id' in self.ticket:
            self.reactor.callLater(0.1, self._on_message, message, tag)
            return

        if tag == 'task-completed-%s' % self.ticket['ticket_id']:
            self._task_completed(message)


        elif tag == 'task-failed-%s' % self.ticket['ticket_id']:
            self._task_failed(message)


        elif tag == 'log-%s' % self.ticket['ticket_id']:
            try:
                data = json.loads(message)
                if 'status' in data and 'progress' in data:
                    sys.stdout.write('\r[%s] %s: %s' % (data['id'], data['status'], data['progress']))

                elif 'status' in data and 'id' in data:
                    sys.stdout.write('\n[%s] %s' % (data['id'], data['status']))

                elif 'status' in data:
                    sys.stdout.write('\n%s' % (data['status']))

                else:
                    if isinstance(data, basestring):
                        sys.stdout.write(data)
                    else:
                        print pprintpp.pformat(data)

            except ValueError:
                print(message)

    def init(self, name, path, **kwargs):

        def on_result(data):
            print 'result: %s' % pprintpp.pformat(data)

        self._remote_exec('init', on_result, name, os.path.realpath(path))

    def list(self, **kwargs):

        def on_result(data):

            x = PrettyTable(["Application name", "status", "services"], hrules=ALL)
            for app in data:

                services = []
                for service in app['services']:
                     name = service['name']
                     if name.endswith(app['name']):
                         name = name[0:-len(app['name']) - 1]

                     data = '%s (%s)' % (name, 'ON' if service['running'] else 'OFF')

                     if service['ip']:
                         data += ' ip: %s' % service['ip']

                     services.append(data)

                x.add_row([app['name'], (app['status'] if app['running'] else ''), '\n'.join(services)])

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

    def inspect(self, name, service, **kwargs):

        def on_result(data):

            if not isinstance(data, dict):
                print data

            else:

                table = Texttable(max_width=120)
                table.set_cols_dtype(['t',  'a'])
                table.set_cols_width([20,  100])

                rows = [["Name", "Value"]]
                for name, val in data.items():
                    rows.append([name, pprintpp.pformat(val)])

                table.add_rows(rows)
                print table.draw() + "\\n"

        self._remote_exec('inspect', on_result, name, service)

    def remove(self, name, **kwargs):

        def on_result(data):
            print 'result: %s' % pprintpp.pformat(data)

        self._remote_exec('remove', on_result, name)

    def start(self, name, **kwargs):

        def on_result(data):
            print 'result: %s' % pprintpp.pformat(data)

        self._remote_exec('start', on_result, name)

    def stop(self, name, **kwargs):

        def on_result(data):
            print 'result: %s' % pprintpp.pformat(data)

        self._remote_exec('stop', on_result, name)


    def list_deployments(self, **kwargs):

        def on_result(data):
            print 'result: %s' % pprintpp.pformat(data)

        self._remote_exec('deployments', on_result)


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

    cmd = subparsers.add_parser('start', help='Start application')
    cmd.add_argument('name', help='App name')
    cmd.set_defaults(func='start')

    cmd = subparsers.add_parser('stop', help='Stop application')
    cmd.add_argument('name', help='App name')
    cmd.set_defaults(func='stop')

    cmd = subparsers.add_parser('list_deployments', help='Stop application')
    cmd.set_defaults(func='list_deployments')

    cmd = subparsers.add_parser('inspect', help='Inspect application service')
    cmd.add_argument('name', help='App name')
    cmd.add_argument('service', help='Service name')
    cmd.set_defaults(func='inspect')


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



