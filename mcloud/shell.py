import sys
import readline
from autobahn.twisted.util import sleep

from bashutils.colors import color_text
import inject
from mcloud.interrupt import InterruptCancel
from mcloud.rpc_client import subparsers, arg_parser, ApiRpcClient, ClientProcessInterruptHandler
import os
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks


def green(text):
    print(color_text(text, color='green'))

def yellow(text):
    print(color_text(text, color='blue', bcolor='yellow'))

def info(text):
    print()


class ShellCancelInterruptHandler(object):

    def interrupt(self, last=None):
        if last is None:
            print('Hit Ctrl+D for exit.')
        raise InterruptCancel()


@inlineCallbacks
def mcloud_shell(host_ref=None):

    settings = inject.instance('settings')
    interrupt_manager = inject.instance('interrupt_manager')

    readline.parse_and_bind('tab: complete')

    if host_ref:
        app, host = host_ref.split('@')
        state = {
            'app': app,
            'host': host,
        }
    else:
        state = {
            'app': None,
            'host': 'me',
        }

    def use(name, **kwargs):
        if '@' in name:
            app, host = name.split('@')
            if host.strip() == '':
                host = 'me'
            if app.strip() == '':
                app = None

            state['app'] = app
            state['host'] = host
        else:
            state['app'] = name

    cmd = subparsers.add_parser('use')
    cmd.add_argument('name', help='Application name', default=None, nargs='?')
    cmd.set_defaults(func=use)

    from mcloud.logo import logo
    print(logo)

    histfile = os.path.join(os.path.expanduser("~"), ".mcloud_history")
    try:
        readline.read_history_file(histfile)
    except IOError:
        pass

    interrupt_manager.append(ShellCancelInterruptHandler())  # prevent stop reactor on Ctrl + C

    line = ''
    while line != 'exit':

        print('')
        prompt = 'mcloud: %s@%s> ' % (state['app'] or '~', state['host'])

        try:
            line = None

            yield sleep(0.05)

            line = raw_input(color_text(prompt, color='white', bcolor='blue') + ' ')

            if line.startswith('!'):
                os.system(line[1:])
                continue

            if line == '':
                continue

            if line == 'exit':
                break

            readline.write_history_file(histfile)

            params = line.split(' ')
            args = arg_parser.parse_args(params)

            args.argv0 = sys.argv[0]

            if args.host:
                host = args.host
            elif state['host'] == 'me' or not state['host']:
                host = '127.0.0.1'
            else:
                host = state['host']
            client = ApiRpcClient(host=host, settings=settings)
            interrupt_manager.append(ClientProcessInterruptHandler(client))

            for key, val in state.items():
                if not hasattr(args, key) or not getattr(args, key):
                    setattr(args, key, val)

            if isinstance(args.func, str):
                yield getattr(client, args.func)(**vars(args))
            else:
                yield args.func(**vars(args))


        except SystemExit:
            pass

        except EOFError:
            print('')
            break

        except KeyboardInterrupt:
            print('')
            pass

        except Exception as e:
            print '\n  %s\n' % color_text(e.message, color='yellow')

    reactor.callFromThread(reactor.stop)

