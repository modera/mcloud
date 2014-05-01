#!/usr/bin/env python
"""Program entry point"""

from __future__ import print_function

import argparse
from cmd import Cmd
import logging
import pipes
from pydoc import getdoc
import sys
from fabric.state import env
from fabric.contrib.console import confirm

from mfcloud import metadata
from mfcloud.rpc_client import ApiRpcClient, populate_client_parser, CliApiClient
import os
import shlex


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

    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(logging.Formatter())
    console_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)
    root_logger.debug('Logger initialized')


    logging.getLogger("requests").propagate = False

    arg_parser = argparse.ArgumentParser(
        prog=argv[0],

        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=metadata.description,
        epilog=format_epilog())

    arg_parser.add_argument('-e', '--env', help='Environment to use', default='dev')

    arg_parser.add_argument(
        '-V', '--version',
        action='version',
        version='{0} {1}'.format(metadata.project, metadata.version))

    subparsers = arg_parser.add_subparsers()

    populate_client_parser(subparsers)


    def exec_bash(**kwargs):
        shell = os.environ.get('SHELL')
        print('*' * 75)
        print('Executing %s ... Hit Ctrl+d when you are done, to return mfcloud.' % shell)
        print('*' * 75 + '\n')
        os.system(shell)

    cmd = subparsers.add_parser('sh', help='Fetch logs from containers')
    cmd.set_defaults(func=exec_bash)

    # # mfcloud use ubuntu@myserver.com
    # use_cmd = subparsers.add_parser('use', help='Sets target hostname')
    # use_cmd.add_argument('host', help='Hostname with username ex. user@some.server')
    # use_cmd.set_defaults(func='use_host')
    #
    # # mfcloud app create myapp
    # app_create_cmd = subparsers.add_parser('@', help='Executes remote command')
    # app_create_cmd.add_argument('command', help='Name of application', nargs='*')
    # app_create_cmd.set_defaults(func='remote')

    class foo(Cmd):

        intro = '''
            __      _                 _
 _ __ ___  / _| ___| | ___  _   _  __| |
| '_ ` _ \| |_ / __| |/ _ \| | | |/ _` |
| | | | | |  _| (__| | (_) | |_| | (_| |
|_| |_| |_|_|  \___|_|\___/ \__,_|\__,_|

Cloud that loves your data.

'''

        def __init__(self, completekey='tab', stdin=None, stdout=None):

            # self.client = MfcloudDeployment()
            # self.client.init(os.getcwd(), 'dev')

            self.client = CliApiClient()

            Cmd.__init__(self, completekey, stdin, stdout)


        def exec_argparse(self, args):
            args = arg_parser.parse_args(args=args)
            args.argv0 = argv[0]
            if isinstance(args.func, str):
                getattr(self.client, args.func)(**vars(args))
            else:
                args.func(**vars(args))

    foo().exec_argparse(argv[1:])


def entry_point():
    """Zero-argument entry point for use with setuptools/distribute."""
    raise SystemExit(main(sys.argv))


if __name__ == '__main__':
    entry_point()
