import json
import logging
import sys
import time
import uuid
from autobahn.twisted.wamp import ApplicationSession
from autobahn.twisted.websocket import WampWebSocketClientProtocol, WampWebSocketClientFactory
import inject
import re
import os
import pprintpp
from prettytable import PrettyTable, ALL
from texttable import Texttable
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks

class ApiRpcClient(ApplicationSession):

    def __init__(self, host='0.0.0.0', port=7080):
        ApplicationSession.__init__(self)

        self.host = host
        self.port = port

        #self.ticket = {}

        self.on_connect_defered = defer.Deferred()

    @inlineCallbacks
    def start_task(self, task, **kwargs):
        yield getattr(self, task)(**kwargs)
        reactor.stop()


    def onJoin(self, details):
        print("session attached")
        self.on_connect_defered.callback(details)

    def onDisconnect(self):
        print("disconnected")
        self.on_connect_defered.callback(None)
        reactor.stop()

    def onError(self, error):
        print('Ohohoho: %s' % error)

    def onClose(self, *args):
        pass
        reactor.stop()

    def wait_connection(self):
        return self.on_connect_defered


    @inlineCallbacks
    def _remote_exec(self, task_name, on_result, *args):
        try:
            res = yield self.call('mfcloud.%s' % task_name, *args)
            on_result(res)
        except Exception as e:
            print('Failed to execute the task: %s' % e.message)

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
    #        try:
    #            data = json.loads(message)
    #            if 'status' in data and 'progress' in data:
    #                sys.stdout.write('\r[%s] %s: %s' % (data['id'], data['status'], data['progress']))
    #
    #            elif 'status' in data and 'id' in data:
    #                sys.stdout.write('\n[%s] %s' % (data['id'], data['status']))
    #
    #            elif 'status' in data:
    #                sys.stdout.write('\n%s' % (data['status']))
    #            else:
    #                if isinstance(data, basestring):
    #                    sys.stdout.write(data)
    #                else:
    #                    print pprintpp.pformat(data)
    #
    #        except ValueError:
    #            print(message)

    def init(self, name, path, **kwargs):

        if self.host != '127.0.0.1':

            if not path.endswith('/'):
                path += '/'

            if not 'user' in kwargs or kwargs['user'] is None:
                raise ValueError('Please, specify remote user')

            user = kwargs['user']

            remote_path = '/home/%(user)s/mfcloud/%(id)s' % {
                'user': user,
                'id': uuid.uuid1()
            }
            command = 'rsync -v -r %(local)s %(user)s@%(remote)s:%(path)s' % {
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


    def on_print_list_result(self, data):

        x = PrettyTable(["Application name", "Web", "status", "services"], hrules=ALL)
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

            services = []
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

            if app['running']:
                app_status = app['status']
                services_list = '\n'.join(services)
            elif app['status'] == 'error':
                app_status = 'ERROR'
                services_list = app['message']
            else:
                app_status = ''
                services_list = '\n'.join(services)

            if 'web_service' in app and app['web_service']:
                web_service_ = app['web_service']
                if web_service_.endswith(app['name']):
                     web_service_ = web_service_[0:-len(app['name']) - 1]
                web = '%s -> [%s]' % (app['fullname'], web_service_)
            else:
                web = ''

            if 'public_url' in app and app['public_url']:
                web += '\n' + app['public_url']

            x.add_row([app['name'], web, app_status, services_list])

        print x

    def list(self, **kwargs):
        self._remote_exec('list', self.on_print_list_result)


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


    def resolve_volume_port(self, destination):

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


    @inlineCallbacks
    def push(self, source, destination, **kwargs):

        source = yield self.resolve_volume_port(source)
        destination = yield self.resolve_volume_port(destination)

        command = "rsync -v -r %(local_path)s %(remote_path)s" % {
            'local_path': source,
            'remote_path': destination,
        }

        print command

        os.system(command)

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
    cmd.set_defaults(func='list')

    cmd = subparsers.add_parser('remove', help='Remove application')
    cmd.add_argument('name', help='App name')
    cmd.set_defaults(func='remove')

    cmd = subparsers.add_parser('start', help='Start application')
    cmd.add_argument('name', help='App name')
    cmd.set_defaults(func='start')

    cmd = subparsers.add_parser('push', help='Push volume')
    cmd.add_argument('source', help='Push source')
    cmd.add_argument('destination', help='Push destination')
    cmd.set_defaults(func='push')

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

    cmd = subparsers.add_parser('dns', help='List dns records')
    cmd.set_defaults(func='dns')


import argparse
from mfcloud import metadata


log = logging.getLogger(__name__)

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



def main(argv):
    arg_parser = argparse.ArgumentParser(
        prog=argv[0],

        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=metadata.description,
        epilog=format_epilog(),
        add_help=False
    )

    arg_parser.add_argument('-e', '--env', help='Environment to use', default='dev')
    arg_parser.add_argument('-h', '--host', help='Host to use', default='127.0.0.1')

    arg_parser.add_argument(
        '-V', '--version',
        action='version',
        version='{0} {1}'.format(metadata.project, metadata.version))

    subparsers = arg_parser.add_subparsers()

    populate_client_parser(subparsers)


    args = arg_parser.parse_args()

    args.argv0 = argv[0]

    if isinstance(args.func, str):

        def timeout(*args):
            if not hasattr(MfcloudWebSocketClientProtocol, '_mfcloud_connected'):
                print('Connection timeout 3s\n\n\n')
                reactor.stop()
                return


        class MfcloudWebSocketClientProtocol(WampWebSocketClientProtocol):
            def connectionMade(self):

                MfcloudWebSocketClientProtocol._mfcloud_connected = True

                self._session = self.factory._factory()
                WampWebSocketClientProtocol.connectionMade(self)

            def failHandshake(self, reason):
                WampWebSocketClientProtocol.failHandshake(self, reason)

                self._session.onError('Failed handhshake: %s' % reason)


        WampWebSocketClientFactory.protocol = MfcloudWebSocketClientProtocol

        def mfcloud_client(config):
            client = ApiRpcClient(config)

            client.wait_connection()\
                .addCallback(client.start_task, args.func, **vars(args))

            return client

        from autobahn.twisted.wamp import ApplicationRunner

        reactor.callLater(3, timeout)

        runner = ApplicationRunner("ws://127.0.0.1:7080/ws", "realm1", debug=False, debug_app=False, debug_wamp=False)
        runner.run(mfcloud_client)

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
