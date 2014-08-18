import json
import logging
import sys
import uuid
from autobahn.twisted.util import sleep
from confire import Configuration

import re
import os
import pprintpp
from prettytable import PrettyTable, ALL
from texttable import Texttable
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks
from twisted.internet.error import ConnectionRefusedError
from twisted.python import log



class ApiRpcClient(object):

    def __init__(self, host='0.0.0.0', port=7080, settings=None):
        self.host = host
        self.port = port
        self.settings = settings
        self.stop_reactor = True

    @inlineCallbacks
    def _remote_exec(self, task_name, on_result, *args, **kwargs):
        from mfcloud.remote import Client, Task

        client = Client(host=self.host, settings=self.settings)
        try:
            yield client.connect()

            task = Task(task_name)
            task.on_progress = self.print_progress

            try:
                yield client.call(task, *args, **kwargs)

                res = yield task.wait_result()
                on_result(res)

            except Exception as e:
                print('Failed to execute the task: %s' % e.message)

        except ConnectionRefusedError:
            print 'Can\'t connect to mfcloud server'

        client.shutdown()
        yield sleep(0.01)

        if self.stop_reactor:
            reactor.stop()

    #
    #
    #def _on_message(self, message, tag):
    #
    #    logger.debug('zmq message: %s tag: %s', message, tag)
    #
    #    if not 'ticket_id' in self.ticket:
    #        self.reactor.callLater(0.1, self._on_message, message, tag)
    #        return
    #
    #    if tag == 'task-completed-%s' % self.ticket['ticket_id']:
    #        self._task_completed(message)
    #
    #
    #    elif tag == 'task-failed-%s' % self.ticket['ticket_id']:
    #        self._task_failed(message)
    #
    #
    #    elif tag == 'log-%s' % self.ticket['ticket_id']:

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

        self._remote_exec('init', self.on_print_list_result, name, os.path.realpath(path))


    def on_print_list_result(self, data, as_string=False):

        if not data:
            return ''

        x = PrettyTable(["Application name", "Web", "status", "cpu %", "memory", "services"], hrules=ALL)
        for app in data:

            volume_services = {}

            for service in app['services']:
                if service['name'].startswith('_volumes_') and service['running']:
                    name = service['name']
                    #if name.endswith(app['name']):
                    #    name = name[0:-len(app['name']) - 1]
                    name = name[9:]
                    volume_services[name] = '%s' % (
                        #service['ports']['22/tcp'][0]['HostIp'],
                        service['ports']['22/tcp'][0]['HostPort'],
                    )

            service_memory = []
            service_cpu = []
            services = []
            app_cpu = 0.0
            app_mem = 0
            for service in app['services']:
                if service['name'].startswith('_volumes_'):
                    continue

                name = service['name']
                #if name.endswith(app['name']):
                #    name = name[0:-len(app['name']) - 1]

                if service['created']:
                    service_status = 'ON' if service['running'] else 'OFF'
                else:
                    service_status = 'NOT CREATED'

                if service['is_web']:
                    mark = '*'
                else:
                    mark = ''

                data = '%s%s (%s)' % (name, mark, service_status)

                if service['ip']:
                    data += ' ip: %s' % service['ip']

                if name in volume_services:
                    data += ' vol: %s' % volume_services[name]
                    if service['volumes']:
                        data += ' (%s)' % ', '.join(service['volumes'])

                services.append(data)
                service_memory.append(str(service['memory']) + 'M')
                service_cpu.append(("%.2f" % float(service['cpu'])) + '%')

                app_mem += int(service['memory'])
                app_cpu += float(service['cpu'])

            if app['running']:
                app_status = app['status']
                services_list = '\n'.join(services)
                services_cpu_list = '\n'.join(service_cpu) + ('\n-----\n%.2f' % app_cpu) + '%'
                services_memory_list = '\n'.join(service_memory) + ('\n-----\n' + str(app_mem)) + 'M'

            elif app['status'] == 'error':
                app_status = 'ERROR'
                services_list = app['message']
                services_cpu_list = ''
                services_memory_list = ''
            else:
                app_status = ''
                services_list = '\n'.join(services)
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
            else:
                web = ''

            x.add_row([app['name'], web, app_status, services_cpu_list, services_memory_list, services_list])

        if not as_string:
            print x
        else:
            return str(x)

    @inlineCallbacks
    def list(self, follow=False, **kwargs):
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
                yield self._remote_exec('list', _print)
                yield sleep(1)
        else:
            yield self._remote_exec('list', _print)



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


    def dns(self, **kwargs):

        def on_result(data):

            table = Texttable(max_width=120)
            table.set_cols_dtype(['t',  'a'])
            #table.set_cols_width([20,  100])

            rows = [["Name", "Value"]]
            for name, val in data.items():
                rows.append([name, val])

            table.add_rows(rows)
            print table.draw() + "\\n"

        self._remote_exec('dns', on_result)

    def remove(self, name, **kwargs):

        def on_result(data):
            print 'result: %s' % pprintpp.pformat(data)

        self._remote_exec('remove', self.on_print_list_result, name)

    def destroy(self, name, **kwargs):

        def on_result(data):
            print 'result: %s' % pprintpp.pformat(data)

        self._remote_exec('destroy', self.on_print_list_result, name)

    def start(self, name, **kwargs):

        def on_result(data):
            print 'result: %s' % pprintpp.pformat(data)

        self._remote_exec('start', self.on_print_list_result, name)

    def create(self, name, **kwargs):

        def on_result(data):
            print 'result: %s' % pprintpp.pformat(data)

        self._remote_exec('create', self.on_print_list_result, name)

    def format_domain(self, domain, ssl):
        if ssl:
            domain = 'https://%s' % domain
        return domain

    def publish(self, domain, app, ssl=False, **kwargs):

        def on_result(data):
            print 'result: %s' % pprintpp.pformat(data)

        self._remote_exec('publish', self.on_print_list_result, self.format_domain(domain, ssl), app)

    def on_vars_result(self, data):
        x = PrettyTable(["variable", "value"], hrules=ALL)
        for line in data.items():
            x.add_row(line)
        print x

    def set(self, name, val, **kwargs):
        self._remote_exec('set_var', self.on_vars_result, name, val)

    def unset(self, name, **kwargs):
        self._remote_exec('rm_var', self.on_vars_result, name)

    def vars(self, **kwargs):
        self._remote_exec('list_vars', self.on_vars_result)

    def unpublish(self, domain, ssl=False, **kwargs):

        def on_result(data):
            print 'result: %s' % pprintpp.pformat(data)

        self._remote_exec('unpublish', self.on_print_list_result, self.format_domain(domain, ssl))

    def restart(self, name, **kwargs):

        def on_result(data):
            print 'result: %s' % pprintpp.pformat(data)

        self._remote_exec('restart', self.on_print_list_result, name)

    def rebuild(self, name, **kwargs):

        def on_result(data):
            print 'result: %s' % pprintpp.pformat(data)

        self._remote_exec('rebuild', self.on_print_list_result, name)


    def resolve_volume_port(self, destination):

        print destination

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


    @inlineCallbacks
    def push(self, source, destination, **kwargs):

        source = yield self.resolve_volume_port(source)
        destination = yield self.resolve_volume_port(destination)

        command = "rsync -v -r --exclude '.git' %(local_path)s %(remote_path)s" % {
            'local_path': source,
            'remote_path': destination,
        }

        print command

        os.system(command)

    def run(self, service, command='bash', **kwargs):

        service, app = service.split('.')

        def on_result(result):

            os.system("docker run -i -t -v %(hosts_vol)s --dns=%(dns-server)s --dns-search=%(dns-suffix)s --volumes-from=%(container)s %(image)s %(command)s" % {
                'container': '%s.%s' % (service, app),
                'image': result['image'],
                'hosts_vol': '%s:/etc/hosts' % result['hosts_path'],
                'dns-server': result['dns-server'],
                'dns-suffix': '%s.%s' % (app, result['dns-suffix']),
                'command': command
            })

        self._remote_exec('run', on_result, app, service)

    def stop(self, name, **kwargs):

        def on_result(data):
            print 'result: %s' % pprintpp.pformat(data)

        self._remote_exec('stop', self.on_print_list_result, name)


def populate_client_parser(subparsers):


    cmd = subparsers.add_parser('init', help='Creates a new application')
    cmd.add_argument('name', help='App name')
    cmd.add_argument('--user', default=None, help='Remote username')
    cmd.add_argument('path', help='Path', nargs='?', default='.')
    cmd.set_defaults(func='init')

    cmd = subparsers.add_parser('list', help='List registered applications')
    cmd.add_argument('-f', '--follow', default=False, action='store_true', help='Continuously run list command')
    cmd.set_defaults(func='list')

    cmd = subparsers.add_parser('remove', help='Remove application')
    cmd.add_argument('name', help='App name')
    cmd.set_defaults(func='remove')

    cmd = subparsers.add_parser('start', help='Start application')
    cmd.add_argument('name', help='App name')
    cmd.set_defaults(func='start')

    cmd = subparsers.add_parser('create', help='Create application containers')
    cmd.add_argument('name', help='App name')
    cmd.set_defaults(func='create')

    cmd = subparsers.add_parser('restart', help='Start application')
    cmd.add_argument('name', help='App name')
    cmd.set_defaults(func='restart')

    cmd = subparsers.add_parser('rebuild', help='Start application')
    cmd.add_argument('name', help='App name')
    cmd.set_defaults(func='rebuild')

    cmd = subparsers.add_parser('push', help='Push volume')
    cmd.add_argument('source', help='Push source')
    cmd.add_argument('destination', help='Push destination')
    cmd.set_defaults(func='push')

    cmd = subparsers.add_parser('publish', help='Publish an application')
    cmd.add_argument('domain', help='Domain to publish')
    cmd.add_argument('app', help='Application name')
    cmd.add_argument('--ssl', default=False, action='store_true', help='Ssl protocol')
    cmd.set_defaults(func='publish')

    cmd = subparsers.add_parser('set', help='Set environment variable on server')
    cmd.add_argument('name', help='Variable name')
    cmd.add_argument('val', help='Value')
    cmd.set_defaults(func='set')

    cmd = subparsers.add_parser('unset', help='Unset environment variable on server')
    cmd.add_argument('name', help='Variable name')
    cmd.set_defaults(func='unset')

    cmd = subparsers.add_parser('vars', help='List environment variables on server')
    cmd.set_defaults(func='vars')

    cmd = subparsers.add_parser('unpublish', help='Unpublish an application')
    cmd.add_argument('domain', help='Domain to unpublish')
    cmd.add_argument('--ssl', default=False, action='store_true', help='Ssl protocol')
    cmd.set_defaults(func='unpublish')

    cmd = subparsers.add_parser('run', help='Execute command')
    cmd.add_argument('service', help='Service name')
    cmd.add_argument('command', help='Command to execute', default='bash', nargs='?')
    cmd.set_defaults(func='run')

    cmd = subparsers.add_parser('stop', help='Stop application')
    cmd.add_argument('name', help='App name')
    cmd.set_defaults(func='stop')

    cmd = subparsers.add_parser('destroy', help='Destroy application containers')
    cmd.add_argument('name', help='App name')
    cmd.set_defaults(func='destroy')

    cmd = subparsers.add_parser('inspect', help='Inspect application service')
    cmd.add_argument('name', help='App name')
    cmd.add_argument('service', help='Service name')
    cmd.set_defaults(func='inspect')

    cmd = subparsers.add_parser('cert-gen', help='Inspect application service')
    cmd.add_argument('username', help='Your username')
    cmd.add_argument('service', help='Service name')
    cmd.set_defaults(func='inspect')

    cmd = subparsers.add_parser('dns', help='List dns records')
    cmd.set_defaults(func='dns')


    # # # mfcloud use ubuntu@myserver.com
    # fig_cmd = subparsers.add_parser('fig', help='Executes fig commands')
    # fig_cmd.add_argument('--env', help='Environment name', default='dev')
    # fig_cmd.add_argument('--app-name', help='App name')
    # fig_cmd.add_argument('fig_cmd', help='Fig command to execeute')
    # fig_cmd.set_defaults(func=func=fig_main)


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


import argparse

from mfcloud import metadata


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


def get_argparser():
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
    populate_client_parser(subparsers)
    return arg_parser


def main(argv):

    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(logging.Formatter())
    console_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)
    root_logger.debug('Logger initialized')

    logging.getLogger("requests").propagate = False

    arg_parser = get_argparser()

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

        getattr(client, args.func)(**vars(args))

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
