#!/usr/bin/env python
"""Program entry point"""

from __future__ import print_function

import argparse
import logging
from pydoc import getdoc
import sys

from ficloud import metadata
from ficloud.deployment import FicloudDeployment

from ficloud.fig_ext import FigCommand
from fig.cli.docopt_command import NoSuchCommand
from fig.cli.errors import UserError
from fig.cli.main import TopLevelCommand, parse_doc_section
from fig.packages.docker import APIError
from fig.project import NoSuchService, DependencyError
import os

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


def fig_main(env, fig_cmd, app_name, **kwargs):
    # Disable requests logging

    try:
        command = FigCommand(env, app_name)
        command.dispatch(fig_cmd.split(' '), None)
    except KeyboardInterrupt:
        log.error("\nAborting.")
        exit(1)
    except (UserError, NoSuchService, DependencyError) as e:
        log.error(e.msg)
        exit(1)
    except NoSuchCommand as e:
        log.error("No such command: %s", e.command)
        log.error("")
        log.error("\n".join(parse_doc_section("commands:", getdoc(e.supercommand))))
        exit(1)
    except APIError as e:
        log.error(e.explanation)
        exit(1)


def populate_client_parser(subparsers):


    # # # ficloud use ubuntu@myserver.com
    # fig_cmd = subparsers.add_parser('fig', help='Executes fig commands')
    # fig_cmd.add_argument('--env', help='Environment name', default='dev')
    # fig_cmd.add_argument('--app-name', help='App name')
    # fig_cmd.add_argument('fig_cmd', help='Fig command to execeute')
    # fig_cmd.set_defaults(func=func=fig_main)

    cmd = subparsers.add_parser('start', help='Run services as daemons')
    cmd.add_argument('services', help='Service names', nargs='*')
    cmd.add_argument('--no-logs', dest='logs', action='store_false', default=True, help='No logs')
    cmd.set_defaults(func='start')

    cmd = subparsers.add_parser('stop', help='Stop services')
    cmd.add_argument('services', help='Service names', nargs='*')
    cmd.set_defaults(func='stop')

    cmd = subparsers.add_parser('destroy', help='Destory services and containers')
    cmd.add_argument('services', help='Service names', nargs='*')
    cmd.set_defaults(func='destroy')

    cmd = subparsers.add_parser('rebuild', help='Destory services and containers')
    cmd.add_argument('services', help='Service names', nargs='*')
    cmd.set_defaults(func='rebuild')

    cmd = subparsers.add_parser('logs', help='Fetch logs from containers')
    cmd.add_argument('services', help='Service names', nargs='*')
    cmd.set_defaults(func='logs')

    cmd = subparsers.add_parser('volumes', help='Show volumes of current project')
    cmd.add_argument('services', help='Service names', nargs='*')
    cmd.set_defaults(func='list_volumes')

    cmd = subparsers.add_parser('status', help='Show current status of services')
    cmd.set_defaults(func='status')


def main(argv):

    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(logging.Formatter())
    console_handler.setLevel(logging.INFO)
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG)
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

    # ficloud use ubuntu@myserver.com
    use_cmd = subparsers.add_parser('use', help='Sets target hostname')
    use_cmd.add_argument('host', help='Hostname with username ex. user@some.server')
    use_cmd.set_defaults(func='use_host')

    # ficloud app create myapp
    app_create_cmd = subparsers.add_parser('remote', help='Executes remote command')
    app_create_cmd.add_argument('command', help='Name of application', nargs='*')
    app_create_cmd.set_defaults(func='remote')


    if len(argv) > 1:
        args = arg_parser.parse_args(args=argv[1:])
        logging.getLogger().level = logging.DEBUG

        args.argv0 = argv[0]

        client = FicloudDeployment()
        client.init(os.getcwd(), args.env)
        getattr(client, args.func)(**vars(args))

        return 0

    else:
        arg_parser.print_help()
        return 1


def entry_point():
    """Zero-argument entry point for use with setuptools/distribute."""
    raise SystemExit(main(sys.argv))


if __name__ == '__main__':
    entry_point()
