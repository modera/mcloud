#!/usr/bin/env python
"""Program entry point"""

from __future__ import print_function

import argparse
import logging
import sys

from ficloud import metadata
from ficloud.client import FicloudClient
from ficloud.server import FicloudServer
from pywizard.cli import configure_logger


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
        epilog=format_epilog())

    arg_parser.add_argument('--log-level', type=str, help='Log level. Useful ones: DEBUG, INFO, ERROR', default='INFO')

    arg_parser.add_argument(
        '-V', '--version',
        action='version',
        version='{0} {1}'.format(metadata.project, metadata.version))

    subparsers = arg_parser.add_subparsers()

    server = FicloudServer()

    balancer_cmd = subparsers.add_parser('balancer').add_subparsers()

    app_create_cmd = balancer_cmd.add_parser('set', help='Sets new destination for a domain')
    app_create_cmd.add_argument('domain', help='domain name')
    app_create_cmd.add_argument('path', help='destination path')
    app_create_cmd.set_defaults(func=server.balancer_set)

    app_create_cmd = balancer_cmd.add_parser('remove', help='Remove destination for a domain')
    app_create_cmd.add_argument('domain', help='domain name')
    app_create_cmd.set_defaults(func=server.balancer_remove)

    args = arg_parser.parse_args(args=argv[1:])

    logging.getLogger().level = logging.DEBUG

    args.func(**vars(args))

    return 0


def entry_point():
    """Zero-argument entry point for use with setuptools/distribute."""
    raise SystemExit(main(sys.argv))


if __name__ == '__main__':
    entry_point()
