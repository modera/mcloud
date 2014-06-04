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
from mfcloud.rpc_client import ApiRpcClient, populate_client_parser
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

            self.client = ApiRpcClient()

            Cmd.__init__(self, completekey, stdin, stdout)


        def exec_argparse(self, args):
            args = arg_parser.parse_args(args=args)
            args.argv0 = argv[0]
            if isinstance(args.func, str):
                getattr(self.client, args.func)(**vars(args))
            else:
                args.func(**vars(args))

    if len(argv) == 1:
        argv.append('list')

    foo().exec_argparse(argv[1:])


def entry_point():
    """Zero-argument entry point for use with setuptools/distribute."""
    raise SystemExit(main(sys.argv))


if __name__ == '__main__':
    entry_point()
