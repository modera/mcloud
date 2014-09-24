import json
import logging
import sys
import uuid
import argparse

import re
import os
from autobahn.twisted.util import sleep
from confire import Configuration
import pprintpp
from prettytable import PrettyTable, ALL
from texttable import Texttable
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks
from twisted.internet.error import ConnectionRefusedError
from twisted.python import log
from mfcloud import metadata
from mfcloud.sendfile import get_storage, storage_sync


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
    prog='mfcloud',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=metadata.description,
    epilog=format_epilog(),
    add_help=False
)
arg_parser.add_argument('-v', '--verbose', help='Show more logs', action='store_true', default=False)
arg_parser.add_argument('-e', '--env', help='Environment to use', default='dev')
arg_parser.add_argument('-h', '--host', help='Host to use', default='127.0.0.1')
arg_parser.add_argument(
    '-V', '--version',
    action='version',
    version='{0} {1}'.format(metadata.project, metadata.version))

subparsers = arg_parser.add_subparsers()


def cli(help_, arguments=None):
    def cmd_decorator(func):

        cmd = subparsers.add_parser(func.__name__, help=help_)

        if arguments:
            for argument in arguments:
                cmd.add_argument(*argument[0], **argument[1])

        cmd.set_defaults(func=func.__name__)

        def _run(*args, **kwargs):
            func1 = func(*args, **kwargs)
            if reactor.running:
                reactor.stop()
            return func1

        return _run

    return cmd_decorator


def arg(*args, **kwargs):
    return args, kwargs


class ApiRpcClient(object):

    def __init__(self, host='0.0.0.0', port=7080, settings=None):
        self.host = host
        self.port = port
        self.settings = settings

    @inlineCallbacks
    def _remote_exec(self, task_name, *args, **kwargs):
        from mfcloud.remote import Client, Task

        client = Client(host=self.host, settings=self.settings)
        try:
            yield client.connect()

            task = Task(task_name)
            task.on_progress = self.print_progress

            try:
                yield client.call(task, *args, **kwargs)

                res = yield task.wait_result()
                yield client.shutdown()
                yield sleep(0.1)

                defer.returnValue(res)

            except Exception as e:
                print('Failed to execute the task: %s' % e.message)

        except ConnectionRefusedError:
            print 'Can\'t connect to mfcloud server'


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

    @cli('Push appliction volume application', arguments=(
        arg('source', help='Push source'),
        arg('destination', help='Push destination'),
    ))
    @inlineCallbacks
    def sync(self, source, destination, **kwargs):

        src = get_storage(source)
        dst = get_storage(destination)

        yield storage_sync(src, dst, confirm=True, verbose=True)

        yield sleep(0.01)


        # source = yield self.resolve_volume_port(source)
        # destination = yield self.resolve_volume_port(destination)
        #
        # command = "rsync -v -r --exclude '.git' %(local_path)s %(remote_path)s" % {
        #     'local_path': source,
        #     'remote_path': destination,
        # }
        #
        # print command
        #
        # os.system(command)


    @cli('List running tasks')
    @inlineCallbacks
    def ps(self, **kwargs):
        from mfcloud.remote import Client

        client = Client(host=self.host, settings=self.settings)
        try:
            yield client.connect()
            tasks = yield client.task_list()

            print tasks

        except ConnectionRefusedError:
            print 'Can\'t connect to mfcloud server'

        client.shutdown()
        yield sleep(0.01)

        if self.stop_reactor:
            reactor.stop()

    @cli('Kills task', arguments=(
        arg('task_id', help='Id of the task'),
    ))
    @inlineCallbacks
    def kill(self, task_id=None, **kwargs):
        from mfcloud.remote import Client

        client = Client(host=self.host, settings=self.settings)
        try:
            yield client.connect()
            success = yield client.terminate_task(task_id)

            if not success:
                print 'Task not found by id'

            else:
                print 'Task successfully treminated.'

        except ConnectionRefusedError:
            print 'Can\'t connect to mfcloud server'

        client.shutdown()
        yield sleep(0.01)

        if self.stop_reactor:
            reactor.stop()

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

            remote_path = '/%(prefix)s%(user)s/mfcloud/%(id)s' % {
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

        self._remote_exec('init', name, os.path.realpath(path))


    def print_app_details(self, app):

        out = '\n'

        x = PrettyTable(["Service name", "status", "ip",  "cpu %", "memory", "volumes", "public urls"], hrules=ALL)

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
                    web.append(app['fullname'])

                    if 'public_urls' in app and app['public_urls']:
                        for url in app['public_urls']:
                            web.append(url)

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


    @cli('List running processes')
    @inlineCallbacks
    def ps(self, follow=False, **kwargs):
        self.last_lines = 0

        def _print(data):
            ret = self.on_print_list_result(data, as_string=True)

            if self.last_lines > 0:
                print '\033[1A' * self.last_lines

            print ret

            self.last_lines = ret.count('\n') + 2

        if follow:
            self.stop_reactor = False
            while follow:
                ret = yield self._remote_exec('list')
                _print(ret)
                yield sleep(1)
        else:
            ret = yield self._remote_exec('list')
            _print(ret)


    @cli('List registered applications', arguments=(
        arg('name', default=None, help='Application name', nargs='?'),
        arg('-f', '--follow', default=False, action='store_true', help='Continuously run list command'),
    ))
    @inlineCallbacks
    def list(self, name=None, follow=False, **kwargs):
        self.last_lines = 0

        def _print(data):

            ret = 'App not found.'

            if not name:
                ret = self.print_app_list(data)
            else:
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
            table.set_cols_dtype(['t',  'a'])
            table.set_cols_width([20,  100])

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
        table.set_cols_dtype(['t',  'a'])
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

    @cli('Start containers', arguments=(
        arg('name', help='Container or app name'),
    ))
    @inlineCallbacks
    def start(self, name, **kwargs):
        data = yield self._remote_exec('start', name)
        print 'result: %s' % pprintpp.pformat(data)

    @cli('Create containers', arguments=(
        arg('name', help='Container or app name'),
    ))
    @inlineCallbacks
    def create(self, name, **kwargs):
        data = yield self._remote_exec('create', name)
        print 'result: %s' % pprintpp.pformat(data)

    def format_domain(self, domain, ssl):
        if ssl:
            domain = 'https://%s' % domain
        return domain

    @cli('Publish an application', arguments=(
        arg('domain', help='Domain to publish'),
        arg('app', help='Application name'),
        arg('--ssl', default=False, action='store_true', help='Ssl protocol'),
    ))
    @inlineCallbacks
    def publish(self, domain, app, ssl=False, **kwargs):
        data = yield self._remote_exec('publish', self.format_domain(domain, ssl), app)
        print 'result: %s' % pprintpp.pformat(data)

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
        data = yield self._remote_exec('set_var', self.on_vars_result, name, val)

    @cli('Unset variable value', arguments=(
        arg('name', help='Variable name'),
    ))
    @inlineCallbacks
    def unset(self, name, **kwargs):
        data = yield self._remote_exec('rm_var', self.on_vars_result, name)

    @cli('List variables')
    @inlineCallbacks
    def vars(self, **kwargs):
        data = yield self._remote_exec('list_vars', self.on_vars_result)

    @cli('Unpublish an application', arguments=(
        arg('domain', help='Domain to publish'),
        arg('--ssl', default=False, action='store_true', help='Ssl protocol'),
    ))
    @inlineCallbacks
    def unpublish(self, domain, ssl=False, **kwargs):
        data = yield self._remote_exec('unpublish', self.format_domain(domain, ssl))
        print 'result: %s' % pprintpp.pformat(data)

    @cli('Start application', arguments=(
        arg('name', help='App name'),
    ))
    @inlineCallbacks
    def restart(self, name, **kwargs):
        data = yield self._remote_exec('restart', name)
        print 'result: %s' % pprintpp.pformat(data)

    @cli('Rebuild application', arguments=(
        arg('name', help='App name'),
    ))
    @inlineCallbacks
    def rebuild(self, name, **kwargs):
        data = yield self._remote_exec('rebuild', name)
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


    @cli('Run command in container', arguments=(
        arg('service', help='Service name'),
        arg('command', help='Command to execute', default='bash', nargs='?'),
        arg('--no-tty', default=False, action='store_true', help='Disable tty binding'),
    ))
    @inlineCallbacks
    def run(self, service, command='bash', no_tty=False, **kwargs):

        service, app = service.split('.')

        result = yield self._remote_exec('run', app, service)
        os.system("docker run -i %(options)s-v %(hosts_vol)s --dns=%(dns-server)s --dns-search=%(dns-suffix)s --volumes-from=%(container)s %(image)s %(command)s" % {
                'container': '%s.%s' % (service, app),
                'image': result['image'],
                'hosts_vol': '%s:/etc/hosts' % result['hosts_path'],
                'dns-server': result['dns-server'],
                'dns-suffix': '%s.%s' % (app, result['dns-suffix']),
                'command': command,
                'options': '-t' if not no_tty else ''
            })

    @cli('Stop application', arguments=(
        arg('name', help='App name'),
    ))
    @inlineCallbacks
    def stop(self, name, **kwargs):
        data = yield self._remote_exec('stop', name)
        print 'result: %s' % pprintpp.pformat(data)


def main(argv):

    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(logging.Formatter())
    console_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)
    root_logger.debug('Logger initialized')

    logging.getLogger("requests").propagate = False

    args = arg_parser.parse_args()


    if args.verbose:
        log.startLogging(sys.stdout)

    args.argv0 = argv[0]


    class SslConfiguration(Configuration):
        enabled = False
        key = '/etc/mfcloud/ssl.key'
        cert = '/etc/mfcloud/ssl.crt'

    class MyAppConfiguration(Configuration):

        CONF_PATHS = [
            '/etc/mfcloud/mfcloud-client.yml',
            # os.path.expanduser('~/.myapp.yaml'),
            # os.path.abspath('conf/myapp.yaml')
        ]

        haproxy = False

        ssl = SslConfiguration()

    settings = MyAppConfiguration.load()

    client = ApiRpcClient(host=args.host, settings=settings)

    if isinstance(args.func, str):
        log.msg('Starting task: %s' % args.func)

        @inlineCallbacks
        def do_call():
            yield getattr(client, args.func)(**vars(args))
            sleep(0.01)
            reactor.stop()

        do_call()

        reactor.run()
    else:
        args.func(**vars(args))




# intro = '''
#            __      _                 _
# _ __ ___  / _| ___| | ___  _   _  __| |
#| '_ ` _ \| |_ / __| |/ _ \| | | |/ _` |
#| | | | | |  _| (__| | (_) | |_| | (_| |
#|_| |_| |_|_|  \___|_|\___/ \__,_|\__,_|
#
#Cloud that loves your data.
#
#'''

def entry_point():
    """Zero-argument entry point for use with setuptools/distribute."""
    raise SystemExit(main(sys.argv))


if __name__ == '__main__':
    entry_point()
