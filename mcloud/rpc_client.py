from difflib import unified_diff, Differ
import json
import shutil
import sys
from tempfile import mkdtemp
import uuid
import argparse
import subprocess
from contextlib import contextmanager
from bashutils.colors import color_text
import inject
from mcloud.application import Application
from mcloud.attach import AttachStdinProtocol
from mcloud.config import YamlConfig
from mcloud.sync import get_storage, rsync_folder
from mcloud.util import txtimeout

import re
import os
from autobahn.twisted.util import sleep
import pprintpp
from prettytable import PrettyTable, ALL
from texttable import Texttable
from twisted.internet import defer, stdio
from twisted.internet.defer import inlineCallbacks, CancelledError, returnValue
from twisted.internet.error import ConnectionRefusedError
from mcloud import metadata
import yaml
from twisted.internet import reactor


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
    add_help=True
)
arg_parser.add_argument('-v', '--verbose', help='Show more logs', action='store_true', default=False)
arg_parser.add_argument('--host', help='Host to use', default=None)
arg_parser.add_argument(
    '-V', '--version',
    action='version',
    version='{0} {1}'.format(metadata.project, metadata.version))

subparsers = arg_parser.add_subparsers()

command_settings = {}


class LocalCommand(object):
    def __init__(self, config, command):
        self.config = config
        self.command = command

    @inlineCallbacks
    def call(self, to=None, **kwargs):

        try:
            host = config.get_command_host(name=to)
        except KeyError:
            raise Exception('Host alias not found.')

        settings = inject.instance('settings')

        uuid_ = uuid.uuid1()

        for line in self.command['commands']:

            line = line.replace('{host}', host)
            line = line.replace('{uuid}', uuid_)

            print(color_text(line, color='white', bcolor='blue'))

            params = line.split(' ')
            args = arg_parser.parse_args(params)

            args.argv0 = sys.argv[0]

            client = ApiRpcClient(host='127.0.0.1', settings=settings)

            if isinstance(args.func, str):
                yield getattr(client, args.func)(**vars(args))
            else:
                yield args.func(**vars(args))


def load_commands(config):
    """
    :param config:
    :type config: mcloud.config.YamlConfig
    :return:
    """

    for name, command in config.get_commands().items():
        cmd_instance = LocalCommand(config, command)

        cmd = subparsers.add_parser('*%s' % name, help=command['help'])
        cmd.add_argument('to', help='Host to use with command', default=None, choices=config.hosts, nargs='?')
        cmd.set_defaults(func=cmd_instance.call)


if os.path.exists('mcloud.yml'):
    config = YamlConfig(file='mcloud.yml')
    config.load(process=False)

    load_commands(config)


def cli(help_, arguments=None, by_ref=False, name=None):
    def cmd_decorator(func):

        cmd = subparsers.add_parser(name or func.__name__.replace('_', '-'), help=help_)

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
            ret = func(*args, **kwargs)
            return ret

        return _run

    return cmd_decorator


def arg(*args, **kwargs):
    return args, kwargs


class CommandFailedException(Exception):
    pass


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
    def __init__(self, host=None, settings=None):

        if not host:
            # manual variable
            if 'MCLOUD_HOST' in os.environ:
                host = os.environ['MCLOUD_HOST']

            # automatic when using docker container-link
            elif 'MCLOUD_PORT' in os.environ:
                host = os.environ['MCLOUD_PORT']
                if host.startswith('tcp://'):
                    host = host[6:]
            else:
                host = '127.0.0.1'

        if ':' in host:
            host, port = host.split(':')
        else:
            port = 7080

        self.host = host
        self.port = int(port)
        self.settings = settings

        self.current_client = None
        self.current_task = None

    @contextmanager
    def override_host(self, host):
        back = self.host
        self.host = host
        yield
        self.host = back

    @inlineCallbacks
    def _remote_exec(self, task_name, *args, **kwargs):
        from mcloud.remote import Client, Task

        client = Client(host=self.host, port=self.port, settings=self.settings)
        self.current_client = client

        yield txtimeout(client.connect(), 20, 'Can\'t connect to the server on host %s' % self.host)

        task = Task(task_name)
        task.on_progress = self.print_progress

        self.current_task = task

        yield client.call(task, *args, **kwargs)

        res = yield task.wait_result()
        yield client.shutdown()
        yield sleep(0.1)

        defer.returnValue(res)

    def print_progress(self, message):

        try:
            data = json.loads(message)

            if not isinstance(data, dict):
                raise ValueError

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

        except ValueError as e:
            message = message.encode('utf-8')
            sys.stdout.write(message)

    @inlineCallbacks
    def _exec_remote_with_pty(self, task_name, *args):
        stream_proto = AttachStdinProtocol()
        stdio.StandardIO(stream_proto)

        from mcloud.remote import Client, Task

        client = Client(host=self.host, port=self.port, settings=self.settings)
        try:
            yield txtimeout(client.connect(), 20, 'Can\'t connect to the server on host %s' % self.host)

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

        if app['status'] == 'error':
            print ''
            print 'Some errors occurred when receiving application information:'
            for service in app['services']:
                print '\n ' + service['name'] + ':'
                print '  - ' + service['error']

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
                    for target in app['public_urls']:
                        url_ = target['url'] + '/'
                        if 'port' in target and target['port']:
                            url_ += ' -> :' + target['port']

                        if not url_.startswith('http://'):
                            url_ = 'http://' + url_

                        if not 'service' in target and 'web_service' in app and app['web_service'] == service['name']:
                            web.append(url_)

                        if 'service' in target and target['service'] == service['shortname']:
                            web.append(url_)

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

        x = PrettyTable(["Application name", "deployment", "status", "cpu %", "memory", "Web", "Path"], hrules=ALL)
        x.align = 'l'
        for app in data:

            app_cpu = 0.0
            app_mem = 0
            web = ''

            service_status = ''

            for service in app['services']:
                app_mem += int(service['memory'])
                app_cpu += float(service['cpu'])

                if service['created']:
                    service_status += ('^' if service['running'] else 'o')
                else:
                    service_status = 'x'

            app_status = service_status
            services_cpu_list = ('%.2f' % app_cpu) + '%'
            services_memory_list = str(app_mem) + 'M'

            if app['status'] != 'error':
                web_service_ = None
                if 'web_service' in app and app['web_service']:
                    web_service_ = app['web_service']
                    if web_service_.endswith(app['name']):
                        web_service_ = web_service_[0:-len(app['name']) - 1]

                if web_service_:
                    web = '%s -> [%s]' % (app['fullname'], web_service_)

                if 'public_urls' in app and app['public_urls']:
                    for target in app['public_urls']:
                        url_ = target['url'] + '/'

                        if not url_.startswith('http://'):
                            url_ = 'http://' + url_
                        if 'service' in target and target['service']:
                            web += '\n' + '%s -> [%s:%s]' % (
                            url_, target['service'], target['port'] if 'port' in target else '')
                        else:
                            if web_service_:
                                web += '\n' + '%s -> [%s]' % (url_, web_service_)
            else:
                app_status = '!error!'

            app_deployment = app['config']['deployment']
            app_path = app['config']['path']

            x.add_row([app['name'], app_deployment, app_status, services_cpu_list, services_memory_list, web,
                       app_path])

        return '\n' + str(x) + '\n'

    def format_app_srv(self, app, service):
        if service:
            name = '%s.%s' % (service, app)
        else:
            name = app
        return name

    def format_domain(self, domain, ssl):
        if ssl:
            domain = 'https://%s' % domain
        return domain

    ip_regex = r'(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])'
    host_regex = r'(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])'

    def parse_app_ref(self, ref, args, require_service=False, app_only=False, require_app=True, require_host=False):

        app = None
        service = None
        host = None

        if 'app' in args:
            app = args['app']

        if ref:
            ref = ref.strip()

            if ref != '':
                match = re.match('^((%s)\.)?(%s)?(@(%s|%s))?$' % (
                    Application.SERVICE_REGEXP,
                    Application.APP_REGEXP,
                    self.ip_regex,
                    self.host_regex
                ), ref)
                if match:
                    if match.group(2):
                        service = match.group(2)

                    if match.group(3):
                        app = match.group(3)

                    if match.group(5):
                        host = match.group(5)
                else:
                    raise ValueError('Can not parse application/service name')

        if not app and require_app:
            app = os.path.basename(os.getcwd())
            print('Using folder name as application name: %s\n' % app)
            # raise ValueError('You should provide application name.')

        if service and app_only:
            raise ValueError('Command cannot be applied to single service')

        if not service and require_service:
            raise ValueError('Command requires to specify a service name')

        if not host:
            host = self.host

        if require_host:
            return host, app, service
        else:
            return app, service

    @inlineCallbacks
    def get_app(self, app_name):
        ret = yield self._remote_exec('list')
        for app in ret:
            if app['name'] == app_name:
                defer.returnValue(app)

    def on_vars_result(self, data):
        x = PrettyTable(["variable", "value"], hrules=ALL)
        for line in data.items():
            x.add_row(line)
        print x

    def get_volume_config(self, destination):

        match = re.match('^([a-z0-9]+)\.([a-z0-9]+):(.*)$', destination)
        if not match:
            if not destination.endswith('/'):
                destination += '/'
            return defer.succeed(destination)

        d = defer.Deferred()
        service, app, volume = match.group(1), match.group(2), match.group(3)

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

    ############################################################
    # Overview
    ############################################################

    @cli('Execute mcloud shell', arguments=(
            arg('shell', help='Continuously run list command'),
    ))
    @inlineCallbacks
    def shell(self, **kwargs):
        pass  # handled without argparser

    @cli('List registered applications', arguments=(
            arg('-f', '--follow', default=False, action='store_true', help='Continuously run list command'),
    ))
    @inlineCallbacks
    def list(self, follow=False, **kwargs):
        self.last_lines = 0

        def _print(data):
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

    ############################################################
    # Application life-cycle
    ############################################################


    @cli('Creates a new application', arguments=(
            arg('ref', help='Application and service name', default=None, nargs='?'),
            arg('path', help='Path', nargs='?', default='.'),
            arg('--deployment', help='Deployment', default=None),
            arg('--env', help='Application environment'),
            arg('--config', help='Config to use', default=None),
    ))
    @inlineCallbacks
    def init(self, ref, path, config=None, env=None, deployment=None, sync=False, **kwargs):

        app, service = self.parse_app_ref(ref, kwargs, app_only=True)

        if config:
            config_file = os.path.expanduser(config)
        else:
            config_file = os.path.join(path, 'mcloud.yml')

        config = YamlConfig(file=config_file, app_name=app)
        config.load(process=False)

        deployment_info = yield self._remote_exec('deployment_info', name=deployment)

        if deployment_info:
            if not deployment:
                deployment = deployment_info['name']

            if not deployment_info['local']:
                yield self._remote_exec('init', app, config=config.export(), env=env, deployment=deployment)
                if sync:
                    yield self.sync(os.path.realpath(path), '%s@%s' % (app, self.host), no_remove=False, force=True,
                                    full=True)
            else:
                yield self._remote_exec('init', app, path=os.path.realpath(path), config=config.export(),
                                        deployment=deployment)

        else:
            print('There is no deployments configured yet.\n\n'
                  'You can create new local deployment using following command:\n'
                  '\n  $ mcloud deployment-create local\n\n')

            reactor.stop()

    def represent_ordereddict(self, dumper, data):
        value = []

        for item_key, item_value in data.items():
            node_key = dumper.represent_data(item_key)
            node_value = dumper.represent_data(item_value)

            value.append((node_key, node_value))

        return yaml.nodes.MappingNode(u'tag:yaml.org,2002:map', value)

    @cli('Application configuration', arguments=(
            arg('ref', help='Application and service name', default=None, nargs='?'),
            arg('--set-env', help='Set application environment'),
            arg('--config', help='Config to use', nargs='?', default=None),
            arg('--update', default=False, action='store_true', help='Update config'),
            arg('--diff', default=False, action='store_true', help='Show diff only, do not update'),
    ))
    @inlineCallbacks
    def config(self, ref, diff=False, config=None, update=False, set_env=None, **kwargs):
        app, service = self.parse_app_ref(ref, kwargs, app_only=True)

        app_config = yield self._remote_exec('config', app)

        parser_env = set_env or app_config['env']

        if diff or (not update and not set_env):
            old_config = YamlConfig(source=unicode(app_config['source']), app_name=app, env=parser_env)
            old_config.load(process=False)
            from collections import OrderedDict

            yaml.add_representer(unicode, yaml.representer.SafeRepresenter.represent_unicode)
            yaml.add_representer(OrderedDict, self.represent_ordereddict)
            olds = yaml.dump(old_config.config, default_flow_style=False)

        if not update and not diff and not set_env:
            x = PrettyTable(["Name", "Value"], hrules=ALL, align='l', header=False)
            x.align = "l"
            x.add_row(['Config', olds])
            x.add_row(['Environment', app_config['env']])
            x.add_row(['Path', app_config['path']])
            print(x)

        else:
            if config:
                config_file = os.path.expanduser(config)
            else:
                config_file = os.path.join(app_config['path'], 'mcloud.yml')

            new_config = YamlConfig(file=config_file, app_name=app, env=parser_env)
            new_config.load(process=False)

            if diff:
                yaml.add_representer(unicode, yaml.representer.SafeRepresenter.represent_unicode)
                yaml.add_representer(OrderedDict, self.represent_ordereddict)
                news = yaml.dump(new_config.config, default_flow_style=False)

                if olds == news:
                    print('Configs are identical.')
                else:

                    for line in unified_diff(olds.splitlines(1), news.splitlines(1)):
                        if line.endswith('\n'):
                            line = line[0:-1]
                        if line.startswith('+'):
                            print color_text(line, color='green')
                        elif line.startswith('-'):
                            print color_text(line, color='red')
                        else:
                            print line
            else:
                if set_env and not update:
                    yield self._remote_exec('update', app, env=set_env)
                else:
                    yield self._remote_exec('update', app, config=new_config.export(), env=set_env)

    ############################################################

    @cli('Remove containers', arguments=(
            arg('ref', help='Application and service name', default=None, nargs='?'),
    ))
    @inlineCallbacks
    def remove(self, ref, **kwargs):
        app, service = self.parse_app_ref(ref, kwargs, app_only=True)
        data = yield self._remote_exec('remove', self.format_app_srv(app, service))
        print 'result: %s' % pprintpp.pformat(data)

    @cli('Set app deployment', arguments=(
            arg('ref', help='Application name', default=None, nargs='?'),
            arg('deployment', help='Deployment name', default=None, nargs='?'),
    ))
    @inlineCallbacks
    def set_deployment(self, ref, deployment, **kwargs):
        app, service = self.parse_app_ref(ref, kwargs, app_only=True)
        yield self._remote_exec('set_deployment', app, deployment)

        yield self.list()

    ############################################################

    @cli('Start containers', arguments=(
            arg('ref', help='Application and service name', default=None, nargs='?'),
            arg('--init', help='Initialize applications if not exist yet', default=False, action='store_true'),
            arg('--env', help='Application environment'),
            arg('--deployment', help='Application deployment'),
    ))
    @inlineCallbacks
    def start(self, ref, init=False, env=None, deployment=None, **kwargs):

        app, service = self.parse_app_ref(ref, kwargs)

        if init:
            app_instance = yield self.get_app(app)

            if not app_instance:
                yield self.init(app, os.getcwd(), env=env, deployment=deployment, sync=True)

        data = yield self._remote_exec('start', self.format_app_srv(app, service))
        print 'result: %s' % pprintpp.pformat(data)

    ############################################################

    @cli('Create containers', arguments=(
            arg('ref', help='Application and service name', default=None, nargs='?'),
    ))
    @inlineCallbacks
    def create(self, ref, **kwargs):
        app, service = self.parse_app_ref(ref, kwargs)
        data = yield self._remote_exec('create', self.format_app_srv(app, service))
        print 'result: %s' % pprintpp.pformat(data)

    ############################################################


    @cli('Destroy containers', arguments=(
            arg('ref', help='Application and service name', default=None, nargs='?'),
            arg('--scrub-data', default=False, action='store_true', help='Force volumes destroy'),
    ))
    @inlineCallbacks
    def destroy(self, ref, **kwargs):
        app, service = self.parse_app_ref(ref, kwargs)
        data = yield self._remote_exec('destroy', self.format_app_srv(app, service))
        print 'result: %s' % pprintpp.pformat(data)

    ############################################################


    @cli('Start application', arguments=(
            arg('ref', help='Application and service name', default=None, nargs='?'),
    ))
    @inlineCallbacks
    def restart(self, ref, **kwargs):
        app, service = self.parse_app_ref(ref, kwargs)
        data = yield self._remote_exec('restart', self.format_app_srv(app, service))
        print 'result: %s' % pprintpp.pformat(data)

    ############################################################

    @cli('Rebuild application', arguments=(
            arg('ref', help='Application and service name', default=None, nargs='?'),
            arg('--scrub-data', default=False, action='store_true', help='Force volumes destroy'),
    ))
    @inlineCallbacks
    def rebuild(self, ref, **kwargs):
        app, service = self.parse_app_ref(ref, kwargs)
        data = yield self._remote_exec('rebuild', self.format_app_srv(app, service))
        print 'result: %s' % pprintpp.pformat(data)

    ############################################################

    @cli('Stop application', arguments=(
            arg('ref', help='Application and service name', default=None, nargs='?'),
    ))
    @inlineCallbacks
    def stop(self, ref, **kwargs):
        app, service = self.parse_app_ref(ref, kwargs)
        data = yield self._remote_exec('stop', self.format_app_srv(app, service))
        print 'result: %s' % pprintpp.pformat(data)

    ############################################################

    @cli('Show application status', arguments=(
            arg('ref', help='Application and service name', default=None, nargs='?'),
            arg('-f', '--follow', default=False, action='store_true', help='Continuously run list command'),
    ))
    @inlineCallbacks
    def status(self, ref, follow=False, **kwargs):

        name, service = self.parse_app_ref(ref, kwargs, app_only=True)

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

    ############################################################


    ############################################################
    # Deployment life-cycle
    ############################################################

    @cli('List deployments', arguments=(
        arg('command', help='Run docker machine commands', default=None, nargs='*'),
    ))
    @inlineCallbacks
    def machine(self, command, **kwargs):
        print '*' * 40
        print command
        print '*' * 40
        yield self._remote_exec('machine', command)

    @cli('List deployments')
    @inlineCallbacks
    def deployments(self, **kwargs):
        data = yield self._remote_exec('deployments')

        x = PrettyTable(["Deployment name", "Default", "host", "port", "local", "tls", "keys (ca|cert|key)"],
                        hrules=ALL)
        x.align = 'l'
        for line in data:
            certs = '|'.join(['x' if line[k] else 'o' for k in ('ca', 'cert', 'key')])
            default = '*' if line['default'] else ''
            x.add_row([line['name'], default, line['host'], line['port'], line['local'], line['tls'], certs])
        print str(x)

    @cli('Create deployment', arguments=(
            arg('deployment', help='Deployment name'),
            arg('ip_host', help='Deployment docker host', default=None, nargs='?'),
            arg('--port', help='Deployment docker port', default=None),
            arg('--tls', default=False, action='store_true', help='Use tls protocol'),
            arg('--remote', default=True, dest='local', action='store_false', help='Deployment is remote'),
    ))
    @inlineCallbacks
    def deployment_create(self, deployment, ip_host=None, port=None, tls=None, local=True, **kwargs):
        data = yield self._remote_exec('deployment_create', name=deployment, host=ip_host, port=port, tls=tls,
                                       local=local)

        yield self.deployments()

    @cli('update deployment', arguments=(
            arg('deployment', help='Deployment name'),
            arg('ip_host', help='Deployment docker host', default=None, nargs='?'),
            arg('--port', help='Deployment docker port', default=None),
            arg('--local', default=None, action='store_true', dest='local', help='Deployment is local'),
            arg('--remote', default=None, action='store_false', dest='local', help='Deployment is remote'),
            arg('--tls', action='store_true', dest='tls', help='Use tls protocol'),
            arg('--no-tls', action='store_false', dest='tls', help='Don\'t use tls protocol'),
    ))
    @inlineCallbacks
    def deployment_update(self, deployment, ip_host=None, port=None, tls=None, local=None, **kwargs):
        data = yield self._remote_exec('deployment_update', name=deployment, host=ip_host, port=port, tls=tls,
                                       local=local)

        yield self.deployments()

    @cli('make deployment default', arguments=(
            arg('deployment', help='Deployment name'),
    ))
    @inlineCallbacks
    def deployment_set_default(self, deployment, host, **kwargs):
        yield self._remote_exec('deployment_set_default', name=deployment)

        yield self.deployments()

    @cli('upload key file to deployment', arguments=(
            arg('deployment', help='Deployment name'),
            arg('--ca', default=False, action='store_true', help='Upload ca'),
            arg('--cert', default=False, action='store_true', help='Upload cert'),
            arg('--key', default=False, action='store_true', help='Upload key'),
            arg('--remove', default=False, action='store_true', help='Remove key'),
            arg('infile', type=argparse.FileType('r'), default=sys.stdin, nargs='?'),
    ))
    @inlineCallbacks
    def deployment_set(self, deployment, ca=False, cert=False, key=False, infile=None, remove=None, **kwargs):
        if remove:
            file_data = False
        else:
            file_data = infile.read()

        data = {}

        if ca:
            data['ca'] = file_data

        if cert:
            data['cert'] = file_data

        if key:
            data['key'] = file_data

        yield self._remote_exec('deployment_update', name=deployment, **data)

        yield self.deployments()

    @cli('remove deployment', arguments=(
            arg('deployment', help='Deployment name'),
    ))
    @inlineCallbacks
    def deployment_remove(self, deployment, **kwargs):
        data = yield self._remote_exec('deployment_remove', name=deployment)
        print 'result: %s' % pprintpp.pformat(data)

        yield self.deployments()

    @cli('Publish an application', arguments=(
            arg('ref', help='Application name'),
            arg('domain', help='Domain to publish'),
            arg('--port', help='Custom target port'),
            arg('--ssl', default=False, action='store_true', help='Ssl protocol'),
    ))
    @inlineCallbacks
    def publish(self, ref, domain, ssl=False, port=None, **kwargs):
        app_name, service = self.parse_app_ref(ref, kwargs, require_app=True)

        app = yield self.get_app(app_name)

        if not app:
            print 'App not found. Can\'t publish'
        else:
            data = yield self._remote_exec('publish', domain_name=self.format_domain(domain, ssl),
                                           app_name=app_name, service_name=service, custom_port=port)

            self.print_app_list(data)

    @cli('Unpublish an application', arguments=(
            arg('ref', help='Application name'),
            arg('domain', help='Domain to unpublish'),
            arg('--ssl', default=False, action='store_true', help='Ssl protocol'),
    ))
    @inlineCallbacks
    def unpublish(self, ref, domain, ssl=False, **kwargs):
        app_name, service = self.parse_app_ref(ref, kwargs, require_app=True)

        data = yield self._remote_exec('unpublish', app_name=app_name, domain_name=self.format_domain(domain, ssl))
        self.print_app_list(data)

    ############################################################
    # Service utilities
    ############################################################

    @cli('Run a command inside container', arguments=(
            arg('ref', help='Application name', default=None, nargs='?'),
            arg('command', help='Command to execute', default='/bin/bash', nargs='?'),
            arg('--no-tty', default=False, action='store_true', help='Disable tty binding'),
    ))
    def run(self, ref, command, no_tty=False, **kwargs):
        host, app, service = self.parse_app_ref(ref, kwargs, require_service=True, require_host=True)

        with self.override_host(host):
            if no_tty:
                return self._remote_exec('run', self.format_app_srv(app, service), command)
            else:
                return self._exec_remote_with_pty('run', self.format_app_srv(app, service), command)

    ############################################################

    @cli('Show container logs', arguments=(
            arg('ref', help='Application and service name', default=None, nargs='?'),
    ))
    @inlineCallbacks
    def logs(self, ref, follow=False, **kwargs):
        app, service = self.parse_app_ref(ref, kwargs, require_service=True)
        ret = yield self._remote_exec('logs', self.format_app_srv(app, service))

    ############################################################

    @cli('Inspect container', arguments=(
            arg('ref', help='Application and service name', default=None, nargs='?'),
    ))
    @inlineCallbacks
    def inspect(self, ref, **kwargs):

        app, service = self.parse_app_ref(ref, kwargs, require_service=True)

        data = yield self._remote_exec('inspect', app, service)

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

    ############################################################
    # File synchronization
    ############################################################

    @cli('Push appliction volume', arguments=(
            arg('volume', help='Volume name'),
            arg('host', help='Host name', default=None, nargs='?'),
            arg('--app', help='Application name', default=None),
            arg('--path', help='Subpath to synchronize', default=None),
            arg('--no-remove', help='Disable removing files on destination', default=False, action='store_true'),
            arg('--update', help='Compare modification time and size, skip if match.', default=False,
                action='store_true'),
            arg('--watch', help='Keep watching and uploading changed files', default=False, action='store_true'),
    ))
    @inlineCallbacks
    def push(self, volume, host, **kwargs):
        app, service = self.parse_app_ref(None, kwargs, app_only=True)
        config = yield self._remote_exec('config', app)

    @cli('Syncronize application volumes', arguments=(
            arg('source', help='source'),
            arg('destination', help='destination'),
            arg('--path', help='Subpath to synchronize', default=None),
            arg('--remove', help='Disable removing files on destination', default=False, action='store_true'),
            arg('--update', help='Compare modification time and size, skip if match.', default=False,
                action='store_true'),
            arg('--watch', help='Keep watching and uploading changed files', default=False, action='store_true'),
    ))
    @inlineCallbacks
    def sync(self, source, destination, **kwargs):

        src_type, src_args = get_storage(source)
        dst_type, dst_args = get_storage(destination)

        if src_type == 'remote' and dst_type == 'local':
            yield rsync_folder(self, src_args, dst_args, options=kwargs)

        elif src_type == 'local' and dst_type == 'remote':
            yield rsync_folder(self, dst_args, src_args, reverse=True, options=kwargs)

        elif src_type == 'remote' and dst_type == 'remote':
            dir_name = mkdtemp()
            dir_storage = get_storage(dir_name)

            yield rsync_folder(self, src_args, dir_storage, options=kwargs)
            yield rsync_folder(self, dst_args, dir_storage, reverse=True, options=kwargs)

            shutil.rmtree(dir_name)

    @cli('Backup application volumes', arguments=(
            arg('source', help='source'),
            arg('volume', help='Volume to backup', default=None),
            arg('destination', help='Destination s3 bucket', default=None)
    ))
    @inlineCallbacks
    def backup(self, source, volume, destination, **kwargs):
        app_name, service = self.parse_app_ref(source, kwargs, require_app=True, require_service=True)
        result = yield self._remote_exec('backup', app_name, service, volume, destination)
        print result

    @cli('Restore application volumes', arguments=(
            arg('source', help='source'),
            arg('volume', help='Volume to backup', default=None),
            arg('destination', help='Destination s3 bucket', default=None)
    ))
    @inlineCallbacks
    def restore(self, source, volume, destination, **kwargs):
        app_name, service = self.parse_app_ref(source, kwargs, require_app=True, require_service=True)
        result = yield self._remote_exec('backup', app_name, service, volume, destination, True)
        print result

    ############################################################
    # Variables
    ############################################################


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

    ############################################################
    # Utils
    ############################################################

    @cli('Cleanup docker images')
    @inlineCallbacks
    def clean(self, **kwargs):
        clean_containers = "docker ps -a -notrunc| grep 'Exit' | awk '{print \$1}' | xargs -L 1 -r docker rm"
        clean_images = "docker images -a -notrunc | grep none | awk '{print \$3}' | xargs -L 1 -r docker rmi"
        os.system(clean_containers)
        os.system(clean_images)

    @cli('List internal dns records')
    @inlineCallbacks
    def dns(self, **kwargs):
        data = yield self._remote_exec('dns')

        table = Texttable(max_width=120)
        table.set_cols_dtype(['t', 'a'])
        # table.set_cols_width([20,  100])

        rows = [["Name", "Value"]]
        for name, val in data.items():
            rows.append([name, val])

        table.add_rows(rows)
        print table.draw() + "\\n"

    ############################################################


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

    ############################################################

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


        ############################################################
