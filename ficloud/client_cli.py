#!/usr/bin/env python
"""Program entry point"""

from __future__ import print_function

import argparse
import logging
from pydoc import getdoc
import sys

from ficloud import metadata
from ficloud.client import FicloudClient
from ficloud.fig_ext import FigCommand
from fig.cli.docopt_command import NoSuchCommand
from fig.cli.errors import UserError
from fig.cli.main import TopLevelCommand, parse_doc_section
from fig.packages.docker import APIError
from fig.project import NoSuchService, DependencyError

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


def fig_main(env, fig_args, **kwargs):
    # Disable requests logging

    try:
        command = FigCommand(env)
        command.dispatch(fig_args, None)
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

    arg_parser.add_argument(
        '-V', '--version',
        action='version',
        version='{0} {1}'.format(metadata.project, metadata.version))

    subparsers = arg_parser.add_subparsers()

    client = FicloudClient()

    # ficloud use ubuntu@myserver.com
    fig_cmd = subparsers.add_parser('fig', help='Executes fig commands')
    fig_cmd.add_argument('--env', help='Environment name', default='dev')
    fig_cmd.add_argument('fig_args', nargs='*')
    fig_cmd.set_defaults(func=fig_main)

    # ficloud use ubuntu@myserver.com
    use_cmd = subparsers.add_parser('use', help='Sets target hostname')
    use_cmd.add_argument('host', help='Hostname with username ex. user@some.server')
    use_cmd.set_defaults(func=client.use_host)

    # ficloud status
    status_cmd = subparsers.add_parser('status', help='Show current status. For now it\'s target hostname')
    status_cmd.set_defaults(func=client.status)

    # ficloud app create myapp
    app_create_cmd = subparsers.add_parser('app-create', help='Creates new application')
    app_create_cmd.add_argument('name', help='Name of application')
    app_create_cmd.set_defaults(func=client.app_create)

    # ficloud app list
    app_create_cmd = subparsers.add_parser('app-list', help='Lists applications')
    app_create_cmd.set_defaults(func=client.app_list)

    # ficloud app remove myapp
    app_create_cmd = subparsers.add_parser('app-remove', help='Removes new application')
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
