#!/usr/bin/env python
"""Program entry point"""

from __future__ import print_function

import argparse
import logging
import sys

from ficloud import metadata
from ficloud.client import FicloudClient
from ficloud.server import FicloudServer

def main(argv):

    arg_parser = argparse.ArgumentParser(
        prog=argv[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=metadata.description)

    arg_parser.add_argument('--log-level', type=str, help='Log level. Useful ones: DEBUG, INFO, ERROR', default='INFO')

    arg_parser.add_argument(
        '-V', '--version',
        action='version',
        version='{0} {1}'.format(metadata.project, metadata.version))

    subparsers = arg_parser.add_subparsers()

    server = FicloudServer()

    app_list_cmd = subparsers.add_parser('app-list', help='List applications deployed')
    app_list_cmd.set_defaults(func=server.list_apps)

    app_versions_cmd = subparsers.add_parser('app-versions', help='List applications versions deployed')
    app_versions_cmd.add_argument('name', help='Application name')
    app_versions_cmd.set_defaults(func=server.list_app_versions)

    app_versions_cmd = subparsers.add_parser('app-create', help='Create new application')
    app_versions_cmd.add_argument('name', help='Application name')
    app_versions_cmd.set_defaults(func=server.create_app)

    app_versions_cmd = subparsers.add_parser('app-deploy', help='Deploy an application')
    app_versions_cmd.add_argument('name', help='Application name')
    app_versions_cmd.add_argument('branch', help='Branch name')
    app_versions_cmd.set_defaults(func=server.deploy_app)



    app_create_cmd = subparsers.add_parser('balancer-set', help='Sets new destination for a domain')
    app_create_cmd.add_argument('domain', help='domain name')
    app_create_cmd.add_argument('path', help='destination path')
    app_create_cmd.set_defaults(func=server.balancer_set)

    app_create_cmd = subparsers.add_parser('balancer-remove', help='Remove destination for a domain')
    app_create_cmd.add_argument('domain', help='domain name')
    app_create_cmd.set_defaults(func=server.balancer_remove)

    if len(argv) > 1:
        args = arg_parser.parse_args(args=argv[1:])
        logging.getLogger().level = logging.DEBUG

        args.func(**vars(args))
        return 0

    else:
        arg_parser.print_help()
        return 1


def entry_point():
    """Zero-argument entry point for use with setuptools/distribute."""
    raise SystemExit(main(sys.argv))


if __name__ == '__main__':
    entry_point()
