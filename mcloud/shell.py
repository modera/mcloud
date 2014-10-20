import json
import logging
import sys
import uuid
import argparse
import readline
import subprocess
from bashutils.colors import color_text
import signal
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
from twisted.internet.defer import inlineCallbacks
from twisted.internet.error import TimeoutError
from twisted.internet.error import ConnectionRefusedError
from twisted.python import log
from mcloud import metadata



def green(text):
    print(color_text(text, color='green'))

def yellow(text):
    print(color_text(text, color='blue', bcolor='yellow'))

def info(text):
    print()

@inlineCallbacks
def mcloud_shell(subparsers, arg_parser):
    readline.parse_and_bind('tab: complete')

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


        from mcloud.logo import logo
        print(logo)

        histfile = os.path.join(os.path.expanduser("~"), ".mcloud_history")
        try:
            readline.read_history_file(histfile)
        except IOError:
            pass

        line = ''
        while line != 'exit':
            print('')
            prompt = 'mcloud: %s@%s> ' % (state['app'] or '~', state['host'])

            try:
                line = None
                line = raw_input(color_text(prompt, color='white', bcolor='blue') + ' ')

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

                for key, val in state.items():
                    if not hasattr(args, key) or not getattr(args, key):
                        setattr(args, key, val)

                if isinstance(args.func, str):
                    yield getattr(client, args.func)(**vars(args))
                else:
                    yield args.func(**vars(args))

            except SystemExit:
                pass
            except KeyboardInterrupt:
                continue
            except EOFError:
                print('')
                break

            except Exception as e:
                print color_text('Error:', color='white', bcolor='red')
                print(e)

        reactor.callFromThread(reactor.stop)


    # def heartbeat():
    #     print "heartbeat"
    #     reactor.callLater(1.0, heartbeat)
    #
    # reactor.callLater(1.0, heartbeat)
