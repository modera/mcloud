#!/usr/bin/env python
"""Program entry point"""

from __future__ import print_function

import argparse
import logging
import sys

from ficloud import metadata
from ficloud.client import FicloudClient
from ficloud.client_cli import populate_client_parser
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

    app_versions_cmd = subparsers.add_parser('app-command', help='List applications versions deployed')
    app_versions_cmd.add_argument('name', help='Application name')
    app_versions_cmd.add_argument('version', help='Version')
    app_versions_cmd.add_argument('command', help='command to run')
    app_versions_cmd.set_defaults(func=server.fig_app_command)

    app_versions_cmd = subparsers.add_parser('app', help='List applications versions deployed')
    app_versions_cmd.add_argument('name', help='Application name')
    app_versions_cmd.add_argument('version', help='Version')
    app_versions_cmd.set_defaults(wrapper=server.ficloud_app_command)
    app_versions_cmd_subparser = app_versions_cmd.add_subparsers()
    populate_client_parser(app_versions_cmd_subparser)

    app_versions_cmd = subparsers.add_parser('app-create', help='Create new application')
    app_versions_cmd.add_argument('name', help='Application name')
    app_versions_cmd.set_defaults(func=server.create_app)

    app_versions_cmd = subparsers.add_parser('app-remove', help='Remove an application')
    app_versions_cmd.add_argument('name', help='Application name')
    app_versions_cmd.set_defaults(func=server.remove_app)

    app_versions_cmd = subparsers.add_parser('app-deploy', help='Deploy an application')
    app_versions_cmd.add_argument('name', help='Application name')
    app_versions_cmd.add_argument('version', help='Version name')
    app_versions_cmd.set_defaults(func=server.deploy_app)



    app_create_cmd = subparsers.add_parser('balancer-set', help='Sets new destination for a domain')
    app_create_cmd.add_argument('domain', help='domain name')
    app_create_cmd.add_argument('path', help='destination path')
    app_create_cmd.set_defaults(func=server.balancer_set)

    app_create_cmd = subparsers.add_parser('balancer-remove', help='Remove destination for a domain')
    app_create_cmd.add_argument('domain', help='domain name')
    app_create_cmd.set_defaults(func=server.balancer_remove)

    app_create_cmd = subparsers.add_parser('balancer-list', help='List all balancers')
    app_create_cmd.set_defaults(func=server.balancer_list)

    app_create_cmd = subparsers.add_parser('balancer-dump', help='Dump haproxy config')
    app_create_cmd.add_argument('source', help='source path')
    app_create_cmd.add_argument('path', help='config path', default='/etc/haproxy/haproxy.cfg', nargs='?')
    app_create_cmd.set_defaults(func=server.balancer_dump)

    app_create_cmd = subparsers.add_parser('inotify-dump', help='Dump inotify config')
    app_create_cmd.add_argument('source', help='source path', default='/home/ficloud/apps-conf', nargs='?')
    app_create_cmd.add_argument('haproxytpl', help='haproxy temp[late path', default='/etc/haproxy/haproxy.cfg.tpl', nargs='?')
    app_create_cmd.set_defaults(func=server.inotify_dump)

    app_create_cmd = subparsers.add_parser('git-post-receive', help='Used by git')
    app_create_cmd.set_defaults(func=server.git_post_receive)


    def exec_cmd(func, **args):
        func(**args)

    arg_parser.set_defaults(wrapper=exec_cmd)

    if len(argv) > 1:
        args = arg_parser.parse_args(args=argv[1:])
        logging.getLogger().level = logging.DEBUG

        args.argv0 = argv[0]

        args.wrapper(**vars(args))

        return 0

    else:
        arg_parser.print_help()
        return 1


def entry_point():
    """Zero-argument entry point for use with setuptools/distribute."""
    raise SystemExit(main(sys.argv))


if __name__ == '__main__':
    entry_point()
