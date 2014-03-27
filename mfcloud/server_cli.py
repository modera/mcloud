#!/usr/bin/env python
"""Program entry point"""

from __future__ import print_function

import argparse
import logging
import sys

from mfcloud import metadata
from mfcloud.client_cli import populate_client_parser
from mfcloud.deployment import MfcloudDeployment
from mfcloud.host import MfcloudHost
import os


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

    host = MfcloudHost()

    app_list_cmd = subparsers.add_parser('app-list', help='List applications deployed')
    app_list_cmd.set_defaults(func=host.list_apps)



    def mfcloud_app_wrpapper(name, version, func, **kwargs):
        """
        Creates new application. Basically, creates new git repo.

        """

        deployment = host.get_deployment(name, version)

        getattr(deployment, func)(**kwargs)

    app_cmd = subparsers.add_parser('app', help='List applications versions deployed')
    app_cmd.add_argument('name', help='Application name')
    app_cmd.add_argument('version', help='Version')
    app_cmd.set_defaults(wrapper=mfcloud_app_wrpapper)
    app_cmd_subparser = app_cmd.add_subparsers()
    populate_client_parser(app_cmd_subparser)

    app_versions_cmd = subparsers.add_parser('app-create', help='Create new application')
    app_versions_cmd.add_argument('name', help='Application name')
    app_versions_cmd.set_defaults(func=host.create_app)

    app_versions_cmd = subparsers.add_parser('app-remove', help='Remove an application')
    app_versions_cmd.add_argument('name', help='Application name')
    app_versions_cmd.set_defaults(func=host.remove_app)

    app_versions_cmd = subparsers.add_parser('app-deploy', help='Deploy an application')
    app_versions_cmd.add_argument('name', help='Application name')
    app_versions_cmd.add_argument('version', help='Version name')
    app_versions_cmd.set_defaults(func=host.deploy_app)

    app_versions_cmd = subparsers.add_parser('app-undeploy', help='Deploy an application')
    app_versions_cmd.add_argument('name', help='Application name')
    app_versions_cmd.add_argument('version', help='Version name')
    app_versions_cmd.set_defaults(func=host.undeploy_app)

    app_create_cmd = subparsers.add_parser('balancer-set', help='Sets new destination for a domain')
    app_create_cmd.add_argument('domain', help='domain name')
    app_create_cmd.add_argument('path', help='destination path')
    app_create_cmd.set_defaults(func=host.balancer_set)

    app_create_cmd = subparsers.add_parser('balancer-remove', help='Remove destination for a domain')
    app_create_cmd.add_argument('domain', help='domain name')
    app_create_cmd.set_defaults(func=host.balancer_remove)

    app_create_cmd = subparsers.add_parser('balancer-list', help='List all balancers')
    app_create_cmd.set_defaults(func=host.balancer_list)

    app_create_cmd = subparsers.add_parser('balancer-dump', help='Dump haproxy config')
    app_create_cmd.add_argument('source', help='source path')
    app_create_cmd.add_argument('path', help='config path', default='/etc/haproxy/haproxy.cfg', nargs='?')
    app_create_cmd.set_defaults(func=host.balancer_dump)

    app_create_cmd = subparsers.add_parser('inotify-dump', help='Dump inotify config')
    app_create_cmd.add_argument('source', help='source path', default='/home/mfcloud/apps-conf', nargs='?')
    app_create_cmd.add_argument('haproxytpl', help='haproxy temp[late path', default='/etc/haproxy/haproxy.cfg.tpl', nargs='?')
    app_create_cmd.set_defaults(func=host.inotify_dump)

    app_create_cmd = subparsers.add_parser('git-post-receive', help='Used by git')
    app_create_cmd.set_defaults(func=host.git_post_receive)


    if len(argv) > 1:
        args = arg_parser.parse_args(args=argv[1:])
        logging.getLogger().level = logging.DEBUG

        args.argv0 = argv[0]

        if hasattr(args, 'wrapper'):
            args.wrapper(**vars(args))
        else:
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
