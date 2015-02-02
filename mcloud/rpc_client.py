from difflib import unified_diff, Differ
import json
import sys
import uuid
import argparse
import subprocess
from contextlib import contextmanager
from bashutils.colors import color_text
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
from twisted.internet.defer import inlineCallbacks, CancelledError
from twisted.internet.error import ConnectionRefusedError
from mcloud import metadata
import yaml


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
    def __init__(self, host='127.0.0.1', port=7080, settings=None):
        self.host = host
        self.port = port
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

        client = Client(host=self.host, settings=self.settings)
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
            # print ":".join("{:02x}".format(ord(c)) for c in message)
            if message[-1] == chr(0x0a):
                sys.stdout.write(message)
            else:
                print(message)


    @inlineCallbacks
    def _exec_remote_with_pty(self, task_name, *args):
        stream_proto = AttachStdinProtocol()
        stdio.StandardIO(stream_proto)

        from mcloud.remote import Client, Task

        client = Client(host=self.host, settings=self.settings)
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

        x = PrettyTable(["Application name", "status", "cpu %", "memory", "Web", "Path"], hrules=ALL)
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
                            web += '\n' + '%s -> [%s:%s]' % (url_, target['service'], target['port'] if 'port' in target else '')
                        else:
                            if web_service_:
                                web += '\n' + '%s -> [%s]' % (url_, web_service_)

            x.add_row([app['name'], app_status, services_cpu_list, services_memory_list, web, app['config']['path']])

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
        arg('--env', help='Application environment'),
        arg('--config', help='Config to use', default=None),
    ))
    @inlineCallbacks
    def init(self, ref, path, config=None, env=None, **kwargs):

        app, service = self.parse_app_ref(ref, kwargs, app_only=True)

        if config:
            config_file = os.path.expanduser(config)
        else:
            config_file = os.path.join(path, 'mcloud.yml')

        config = YamlConfig(file=config_file, app_name=app)
        config.load(process=False)

        if self.host != '127.0.0.1':
            success = yield self._remote_exec('init', app, config=config.export(), env=env)
            if success:
                yield self.sync(path, '%s@%s' % (app, self.host), no_remove=False, force=True, full=True)
        else:
            yield self._remote_exec('init', app, path=os.path.realpath(path), config=config.export())

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
            yaml.add_representer(OrderedDict, yaml.representer.SafeRepresenter.represent_dict)
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

    ############################################################

    @cli('Start containers', arguments=(
        arg('ref', help='Application and service name', default=None, nargs='?'),
        arg('--init', help='Initialize applications if not exist yet', default=False, action='store_true'),
        arg('--env', help='Application environment'),
    ))
    @inlineCallbacks
    def start(self, ref, init=False, env=None, **kwargs):

        app, service = self.parse_app_ref(ref, kwargs)

        if init:
            app_instance = yield self.get_app(app)

            if not app_instance:
                yield self.init(app, os.getcwd(), env=env)


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

    @cli('Publish an application', arguments=(
        arg('ref', help='Application name', default=None, nargs='?'),
        arg('domain', help='Domain to publish'),
        arg('--port', help='Custom target port'),
        arg('--ssl', default=False, action='store_true', help='Ssl protocol'),
    ))
    @inlineCallbacks
    def publish(self, domain, ref, ssl=False, port=None, **kwargs):
        app_name, service = self.parse_app_ref(ref, kwargs, require_app=True)

        app = yield self.get_app(app_name)

        if not app:
            print 'App not found. Can\'t publish'
        else:
            yield self._remote_exec('publish', self.format_domain(domain, ssl), app_name, service, port)

    @cli('Unpublish an application', arguments=(
        arg('domain', help='Domain to unpublish'),
        arg('--ssl', default=False, action='store_true', help='Ssl protocol'),
    ))
    @inlineCallbacks
    def unpublish(self, domain, ssl=False, **kwargs):
        data = yield self._remote_exec('unpublish', self.format_domain(domain, ssl))
        print 'result: %s' % pprintpp.pformat(data)

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
        arg('--update', help='Compare modification time and size, skip if match.', default=False, action='store_true'),
        arg('--watch', help='Keep watching and uploading changed files', default=False, action='store_true'),
    ))
    @inlineCallbacks
    def push(self, volume, host, **kwargs):
        app, service = self.parse_app_ref(None, kwargs, app_only=True)
        config = yield self._remote_exec('config', app)
        print config


    @cli('Syncronize application volumes', arguments=(
        arg('source', help='source'),
        arg('destination', help='destination'),
        arg('--path', help='Subpath to synchronize', default=None),
        arg('--remove', help='Disable removing files on destination', default=False, action='store_true'),
        arg('--update', help='Compare modification time and size, skip if match.', default=False, action='store_true'),
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

        else:
            print('%s to %s is not supported' % (src_type, dst_type))

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
        #table.set_cols_width([20,  100])

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
