#!/usr/bin/env python
"""Program entry point"""

from __future__ import print_function

import argparse
import sys

from ficloud import metadata
from ficloud.client import FicloudClient


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

    arg_parser.add_argument(
        '-V', '--version',
        action='version',
        version='{0} {1}'.format(metadata.project, metadata.version))

    subparsers = arg_parser.add_subparsers()

    client = FicloudClient()

    # ficloud use ubuntu@myserver.com
    use_cmd = subparsers.add_parser('use', help='Sets target hostname')
    use_cmd.add_argument('host', help='Hostname with username ex. user@some.server')
    use_cmd.set_defaults(func=client.use_host)

    # ficloud status
    status_cmd = subparsers.add_parser('status', help='Show current status. For now it\'s target hostname')
    status_cmd.set_defaults(func=client.status)

    app_cmd = subparsers.add_parser('app').add_subparsers()

    # ficloud app create myapp
    app_create_cmd = app_cmd.add_parser('create', help='Creates new application')
    app_create_cmd.add_argument('name', help='Name of application')
    app_create_cmd.set_defaults(func=client.app_create)

    # ficloud app list
    app_create_cmd = app_cmd.add_parser('list', help='Lists applications')
    app_create_cmd.set_defaults(func=client.app_list)

    # ficloud app remove myapp
    app_create_cmd = app_cmd.add_parser('remove', help='Removes new application')
    app_create_cmd.add_argument('name', help='Name of application')
    app_create_cmd.set_defaults(func=client.app_remove)

    args = arg_parser.parse_args(args=argv[1:])

    args.func(**vars(args))

    return 0


def entry_point():
    """Zero-argument entry point for use with setuptools/distribute."""
    raise SystemExit(main(sys.argv))


if __name__ == '__main__':
    entry_point()
