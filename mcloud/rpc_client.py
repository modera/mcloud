import json
import logging
import sys
import uuid
import argparse
import readline
import subprocess
from bashutils.colors import color_text
import signal
from decorator import contextmanager
from mcloud.attach import Terminal, AttachStdinProtocol
from mcloud.sync.client import FileServerError
from mcloud.sync.storage import get_storage, storage_sync
from mcloud.util import txtimeout

import re
import os
from autobahn.twisted.util import sleep
from confire import Configuration
import pprintpp
from prettytable import PrettyTable, ALL
from texttable import Texttable
from twisted.internet import reactor, defer, stdio
from twisted.internet.defer import inlineCallbacks, CancelledError
from twisted.internet.error import TimeoutError
from twisted.internet.error import ConnectionRefusedError
from twisted.python import log
from mcloud import metadata


def format_epilog():
    """Program entry point.

    :param argv: command-line arguments
    :type argv: :class:`list`
    """
    author_strings = []
    for name, email in zip(metadata.authors, metadata.emails):
        author_strings.append('Author: {0} <{1}>'.format(name, email))
    epilog = '''
{project} {version}

{authors}
URL: <{url}>
'''.format(
        project=metadata.project,
        version=metadata.version,
        authors='\n'.join(author_strings),
        url=metadata.url)
    return epilog


arg_parser = argparse.ArgumentParser(
    prog='mcloud',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=metadata.description,
    epilog=format_epilog(),
    add_help=False
)
arg_parser.add_argument('-v', '--verbose', help='Show more logs', action='store_true', default=False)
arg_parser.add_argument('-h', '--host', help='Host to use', default=None)
arg_parser.add_argument(
    '-V', '--version',
    action='version',
    version='{0} {1}'.format(metadata.project, metadata.version))

subparsers = arg_parser.add_subparsers()

command_settings = {}


def cli(help_, arguments=None, by_ref=False, name=None):
    def cmd_decorator(func):

        cmd = subparsers.add_parser(name or func.__name__, help=help_)

        command_settings[func.__name__] = {
            'need_app': False
        }

        if arguments:
            command_settings[func.__name__]['need_app'] = arguments[0][0][0] == 'app'

        if arguments:
            for argument in arguments:
                cmd.add_argument(*argument[0], **argument[1])

        if by_ref:
            cmd.set_defaults(func=func)
        else:
            cmd.set_defaults(func=func.__name__)

        def _run(*args, **kwargs):
            func1 = func(*args, **kwargs)
            return func1

        return _run

    return cmd_decorator


def arg(*args, **kwargs):
    return args, kwargs

class ClientProcessInterruptHandler(object):

    def __init__(self, client):
        super(ClientProcessInterruptHandler, self).__init__()

        self.client = client

    @inlineCallbacks
    def interrupt(self, last=None):
        if self.client.current_client:
            yield self.client.current_client.shutdown()
            yield sleep(0.05)

            if self.client.current_task and self.client.current_task.wait:
                self.client.current_task.wait.cancel()
                yield sleep(0.05)


class ApiRpcClient(object):
    def __init__(self, host='127.0.0.1', port=7080, settings=None):
        self.host = host
        self.port = port
        self.settings = settings

        self.current_client = None
        self.current_task = None

    @inlineCallbacks
    def _remote_exec(self, task_name, *args, **kwargs):
        from mcloud.remote import Client, Task

        client = Client(host=self.host, settings=self.settings)
        self.current_client = client

        try:
            def _connect_failed():
                raise Exception('Can\'t connect to the server on host %s' % self.host)
            yield txtimeout(client.connect(), 3, _connect_failed)
            task = Task(task_name)
            task.on_progress = self.print_progress

            self.current_task = task

            try:
                yield client.call(task, *args, **kwargs)

                res = yield task.wait_result()
                yield client.shutdown()
                yield sleep(0.1)

                defer.returnValue(res)

            except CancelledError as e:
                print('Interrupted by user.')

            except Exception as e:
                print('Failed to execute the task: %s' % e.message)

        except ConnectionRefusedError:
            print 'Can\'t connect to mcloud server'


    def print_progress(self, message):
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


    @inlineCallbacks
    def _exec_remote_with_pty(self, task_name, *args):
        stream_proto = AttachStdinProtocol()
        stdio.StandardIO(stream_proto)

        from mcloud.remote import Client, Task

        client = Client(host=self.host, settings=self.settings)
        try:
            def _connect_failed():
                raise Exception('Can\'t connect to the server on host %s' % self.host)
            yield txtimeout(client.connect(), 3, _connect_failed)

            task = Task(task_name)
            task.on_progress = self.print_progress
            task.on_stdout = stream_proto.write
            stream_proto.listener = task.on_stdin

            try:
                yield client.call(task, *args, size=stream_proto.term.get_size())

                res = yield task.wait_result()
                yield client.shutdown()
                yield sleep(0.1)

                defer.returnValue(res)

            except Exception as e:
                print repr(e)
                print('Failed to execute the task: %s' % e.message)

        except ConnectionRefusedError:
            print 'Can\'t connect to mcloud server'

        finally:
            stream_proto.stop()


    def print_app_details(self, app):

        out = '\n'

        x = PrettyTable(["Service name", "status", "ip", "cpu %", "memory", "volumes", "public urls"], hrules=ALL)

        for service in app['services']:
            if service['created']:
                service_status = 'ON' if service['running'] else 'OFF'
            else:
                service_status = 'NOT CREATED'

            volumes = ''
            if service['volumes']:
                volumes = '\n'.join(service['volumes'])

            web = []

            if app['status'] != 'error':
                if 'web_service' in app and app['web_service'] == service['name']:
                    web.append('http://' + app['fullname'] + '/')

                    if 'public_urls' in app and app['public_urls']:
                        for url in app['public_urls']:
                            web.append('http://' + url + '/')

            x.add_row([
                service['name'],
                service_status,
                service['ip'],
                ("%.2f" % float(service['cpu'])) + '%',
                str(service['memory']) + 'M',
                volumes,
                '\n'.join(web)
            ])

        out += str(x)

        return out


    def print_app_list(self, data):

        x = PrettyTable(["Application name", "status", "cpu %", "memory", "Web", "Path"], hrules=ALL)
        for app in data:

            app_cpu = 0.0
            app_mem = 0
            web = ''

            for service in app['services']:
                app_mem += int(service['memory'])
                app_cpu += float(service['cpu'])

            if app['running']:
                app_status = app['status']
                services_cpu_list = ('%.2f' % app_cpu) + '%'
                services_memory_list = str(app_mem) + 'M'

            elif app['status'] == 'error':
                app_status = 'ERROR: %s' % app['message']
                web = app['message']
                services_cpu_list = ''
                services_memory_list = ''
            else:
                app_status = ''
                services_cpu_list = ''
                services_memory_list = ''

            if app['status'] != 'error':
                web_service_ = 'No web'
                if 'web_service' in app and app['web_service']:
                    web_service_ = app['web_service']
                    if web_service_.endswith(app['name']):
                        web_service_ = web_service_[0:-len(app['name']) - 1]

                web = '%s -> [%s]' % (app['fullname'], web_service_)

                if 'public_urls' in app and app['public_urls']:
                    for url in app['public_urls']:
                        web += '\n' + '%s -> [%s]' % (url, web_service_)

            x.add_row([app['name'], app_status, services_cpu_list, services_memory_list, web, app['config']['path']])

        return '\n' + str(x) + '\n'

    @cli('Run a command inside container', arguments=(
        arg('app', help='Application name', default=None, nargs='?'),
        arg('service', help='Service name'),
        arg('command', help='Command to execute', default='/bin/bash', nargs='?'),
        arg('--no-tty', default=False, action='store_true', help='Disable tty binding'),
    ))
    def run(self, app, service, command, no_tty=True, **kwargs):
        name = '%s.%s' % (service, require(app))
        return self._exec_remote_with_pty('run', name, command)

    @cli('Push appliction volume application', arguments=(
        arg('source', help='Push source'),
        arg('destination', help='Push destination'),
        arg('--no-remove', help='Disable remove files', default=False, action='store_true'),
        arg('--force', help='Don\'t ask confirmation', default=False, action='store_true'),
    ))
    @inlineCallbacks
    def sync(self, source, destination, no_remove, force, **kwargs):

        src = get_storage(source)
        dst = get_storage(destination)

        try:
            yield storage_sync(src, dst, confirm=not force, verbose=True, remove=not no_remove)
        except FileServerError as e:
            print '------------------------'
            print e.message

    @cli('List running tasks')
    @inlineCallbacks
    def ps(self, **kwargs):
        from mcloud.remote import Client

        client = Client(host=self.host, settings=self.settings)
        try:
            yield client.connect()
            tasks = yield client.task_list()

            print tasks

        except ConnectionRefusedError:
            print 'Can\'t connect to mcloud server'

        yield client.shutdown()
        yield sleep(0.01)

    @cli('Kills task', arguments=(
        arg('task_id', help='Id of the task'),
    ))
    @inlineCallbacks
    def kill(self, task_id=None, **kwargs):
        from mcloud.remote import Client

        client = Client(host=self.host, settings=self.settings)
        try:
            yield client.connect()
            success = yield client.terminate_task(task_id)

            if not success:
                print 'Task not found by id'

            else:
                print 'Task successfully treminated.'

        except ConnectionRefusedError:
            print 'Can\'t connect to mcloud server'

        client.shutdown()
        yield sleep(0.01)

    @cli('Creates a new application', arguments=(
        arg('name', help='App name'),
        arg('--user', default=None, help='Remote username'),
        arg('path', help='Path', nargs='?', default='.')
    ))
    def init(self, name, path, **kwargs):

        if self.host != '127.0.0.1':

            if not path.endswith('/'):
                path += '/'

            if not 'user' in kwargs or kwargs['user'] is None:
                raise ValueError('Please, specify remote user')

            user = kwargs['user']

            remote_path = '/%(prefix)s%(user)s/mcloud/%(id)s' % {
                'prefix': 'home/' if not user == 'root' else '',
                'user': user,
                'id': uuid.uuid1()
            }
            command = 'rsync -v --exclude \'.git\' --rsync-path="mkdir -p %(path)s && rsync" -r %(local)s %(user)s@%(remote)s:%(path)s' % {
                'local': path,
                'user': user,
                'path': remote_path,
                'remote': self.host,
            }
            print command
            os.system(command)

            path = remote_path

        def on_result(data):
            print 'result: %s' % pprintpp.pformat(data)

        return self._remote_exec('init', name, os.path.realpath(path))


    @cli('List registered applications', arguments=(
        arg('-f', '--follow', default=False, action='store_true', help='Continuously run list command'),
    ))
    @inlineCallbacks
    def list(self, follow=False, **kwargs):
        self.last_lines = 0

        def _print(data):

            ret = 'App not found.'

            ret = self.print_app_list(data)

            if self.last_lines > 0:
                print '\033[1A' * self.last_lines

            print ret

            self.last_lines = ret.count('\n') + 2

        if follow:
            while follow:
                ret = yield self._remote_exec('list')
                _print(ret)
                yield sleep(1)
        else:
            ret = yield self._remote_exec('list')
            _print(ret)

    @cli('Show application status', arguments=(
        arg('app', help='Application name', default=None, nargs='?'),
        arg('-f', '--follow', default=False, action='store_true', help='Continuously run list command'),
    ))
    @inlineCallbacks
    def status(self, app=None, follow=False, **kwargs):

        name = require(app)

        self.last_lines = 0

        def _print(data):

            ret = 'App not found.'

            for app in data:
                if app['name'] == name:
                    ret = self.print_app_details(app)
                    break

            if self.last_lines > 0:
                print '\033[1A' * self.last_lines

            print ret

            self.last_lines = ret.count('\n') + 2

        if follow:
            while follow:
                ret = yield self._remote_exec('list')
                _print(ret)
                yield sleep(1)
        else:
            ret = yield self._remote_exec('list')
            _print(ret)

    @cli('Show container logs', arguments=(
        arg('name', help='Container name'),
    ))
    @inlineCallbacks
    def logs(self, name, follow=False, **kwargs):
        ret = yield self._remote_exec('logs', name)

    @cli('Inspect container', arguments=(
        arg('name', help='Container name'),
        arg('service', help='Service name'),
    ))
    @inlineCallbacks
    def inspect(self, name, service, **kwargs):
        data = yield self._remote_exec('inspect', name, service)

        if not isinstance(data, dict):
            print data

        else:

            table = Texttable(max_width=120)
            table.set_cols_dtype(['t', 'a'])
            table.set_cols_width([20, 100])

            rows = [["Name", "Value"]]
            for name, val in data.items():
                rows.append([name, pprintpp.pformat(val)])

            table.add_rows(rows)
            print table.draw() + "\\n"


    @cli('List internal dns records')
    @inlineCallbacks
    def dns(self, **kwargs):
        data = yield self._remote_exec('dns')

        table = Texttable(max_width=120)
        table.set_cols_dtype(['t', 'a'])
        #table.set_cols_width([20,  100])

        rows = [["Name", "Value"]]
        for name, val in data.items():
            rows.append([name, val])

        table.add_rows(rows)
        print table.draw() + "\\n"

    @cli('Remove containers', arguments=(
        arg('name', help='Container or app name'),
    ))
    @inlineCallbacks
    def remove(self, name, **kwargs):
        data = yield self._remote_exec('remove', name)
        print 'result: %s' % pprintpp.pformat(data)

    @cli('Destroy containers', arguments=(
        arg('name', help='Container or app name'),
    ))
    @inlineCallbacks
    def destroy(self, name, **kwargs):
        data = yield self._remote_exec('destroy', name)
        print 'result: %s' % pprintpp.pformat(data)

    def format_app_srv(self, app, service):
        require(app)
        if service:
            name = '%s.%s' % (service, app)
        else:
            name = app
        return name

    @cli('Start containers', arguments=(
        arg('app', help='Application name', default=None, nargs='?'),
        arg('service', help='Service name', default=None, nargs='?'),
        arg('--init', help='Initialize applications if not exist yet', default=False, action='store_true'),
    ))
    @inlineCallbacks
    def start(self, app, service, init=False, **kwargs):
        if not app:
            app = os.path.basename(os.getcwd())

        if init:
            app_instance = yield self.get_app(app)

            if not app_instance:
                yield self.init(app, os.getcwd())


        data = yield self._remote_exec('start', self.format_app_srv(app, service))
        print 'result: %s' % pprintpp.pformat(data)

    @cli('Create containers', arguments=(
        arg('app', help='Application name', default=None, nargs='?'),
        arg('service', help='Service name', default=None, nargs='?'),
    ))
    @inlineCallbacks
    def create(self, app, service, **kwargs):
        data = yield self._remote_exec('create', self.format_app_srv(app, service))
        print 'result: %s' % pprintpp.pformat(data)

    def format_domain(self, domain, ssl):
        if ssl:
            domain = 'https://%s' % domain
        return domain

    @inlineCallbacks
    def get_app(self, app_name):
        ret = yield self._remote_exec('list')
        for app in ret:
            if app['name'] == app_name:
                defer.returnValue(app)

    @cli('Publish an application', arguments=(
        arg('app', help='Application name'),
        arg('domain', help='Domain to publish'),

        arg('--ssl', default=False, action='store_true', help='Ssl protocol'),
    ))
    @inlineCallbacks
    def publish(self, domain, app, ssl=False, **kwargs):
        require(app)

        app = yield self.get_app(app)

        if not app:
            print 'App not found. Can\'t publish'
        else:
            yield self._remote_exec('publish', self.format_domain(domain, ssl), app['name'])

    def on_vars_result(self, data):
        x = PrettyTable(["variable", "value"], hrules=ALL)
        for line in data.items():
            x.add_row(line)
        print x

    @cli('Set variable value', arguments=(
        arg('name', help='Variable name'),
        arg('val', help='Value'),
    ))
    @inlineCallbacks
    def set(self, name, val, **kwargs):
        data = yield self._remote_exec('set_var', name, val)
        self.on_vars_result(data)

    @cli('Unset variable value', arguments=(
        arg('name', help='Variable name'),
    ))
    @inlineCallbacks
    def unset(self, name, **kwargs):
        data = yield self._remote_exec('rm_var', name)
        self.on_vars_result(data)

    @cli('List variables')
    @inlineCallbacks
    def vars(self, **kwargs):
        data = yield self._remote_exec('list_vars')
        self.on_vars_result(data)

    @cli('Unpublish an application', arguments=(
        arg('domain', help='Domain to unpublish'),
        arg('--ssl', default=False, action='store_true', help='Ssl protocol'),
    ))
    @inlineCallbacks
    def unpublish(self, domain, ssl=False, **kwargs):
        data = yield self._remote_exec('unpublish', self.format_domain(domain, ssl))
        print 'result: %s' % pprintpp.pformat(data)

    @cli('Start application', arguments=(
        arg('app', help='Application name', default=None, nargs='?'),
        arg('service', help='Service name', default=None, nargs='?'),
    ))
    @inlineCallbacks
    def restart(self, app, service, **kwargs):
        data = yield self._remote_exec('restart', self.format_app_srv(app, service))
        print 'result: %s' % pprintpp.pformat(data)

    @cli('Rebuild application', arguments=(
        arg('app', help='Application name', default=None, nargs='?'),
        arg('service', help='Service name', default=None, nargs='?'),
    ))
    @inlineCallbacks
    def rebuild(self, app, service, **kwargs):
        data = yield self._remote_exec('rebuild', self.format_app_srv(app, service))
        print 'result: %s' % pprintpp.pformat(data)


    def get_volume_config(self, destination):

        match = re.match('^([a-z0-9]+)\.([a-z0-9]+):(.*)$', destination)
        if not match:
            if not destination.endswith('/'):
                destination += '/'
            return defer.succeed(destination)

        d = defer.Deferred()
        service, app, volume = match.group(1), match.group(2), match.group(3)

        print (service, app, volume)

        if not volume.endswith('/'):
            volume += '/'

        def on_result(volume_port):

            destination = "-e 'ssh -p %(port)s' root@%(host)s:%(volume)s" % {
                'port': volume_port,
                'host': self.host,
                'volume': volume
            }

            d.callback(destination)

        self._remote_exec('push', on_result, app, service, volume)

        return d

    @cli('Stop application', arguments=(
        arg('app', help='Application name', default=None, nargs='?'),
        arg('service', help='Service name', default=None, nargs='?'),
    ))
    @inlineCallbacks
    def stop(self, app, service, **kwargs):
        data = yield self._remote_exec('stop', self.format_app_srv(app, service))
        print 'result: %s' % pprintpp.pformat(data)


def require(app):
    if not app:
        raise ValueError(
            'Application name is required. Pass it as an argument, or set it with "use" command in shell mode.')
    return app

