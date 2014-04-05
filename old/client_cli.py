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
from mfcloud.deployment import MfcloudDeployment, project_name_by_dir

from mfcloud.fig_ext import FigCommand
from fig.cli.docopt_command import NoSuchCommand
from fig.cli.errors import UserError
from fig.cli.main import TopLevelCommand, parse_doc_section
from fig.packages.docker import APIError
from fig.project import NoSuchService, DependencyError
import os
import re
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


    # # # mfcloud use ubuntu@myserver.com
    # fig_cmd = subparsers.add_parser('fig', help='Executes fig commands')
    # fig_cmd.add_argument('--env', help='Environment name', default='dev')
    # fig_cmd.add_argument('--app-name', help='App name')
    # fig_cmd.add_argument('fig_cmd', help='Fig command to execeute')
    # fig_cmd.set_defaults(func=func=fig_main)

    cmd = subparsers.add_parser('start', help='Run services as daemons')
    cmd.add_argument('services', help='Service names', nargs='*')
    cmd.add_argument('--no-logs', dest='logs', action='store_false', default=True, help='No logs')
    cmd.add_argument('--rebuild', action='store_true', default=False, help='Rebuild container')
    cmd.set_defaults(func='start')

    cmd = subparsers.add_parser('run', help='Run command on a service')
    cmd.add_argument('service', help='Service name')
    cmd.add_argument('command', help='Command to run')
    cmd.add_argument('--no-tty', dest='disable_tty', action='store_true', default=False, help='No tty')
    cmd.set_defaults(func='run')

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


    # 'PS1=(.env)\[\e]0;\u@\h: \w\a\]${debian_chroot:+($debian_chroot)}\u@\h:\w\$'

    def exec_bash(**kwargs):
        shell = os.environ.get('SHELL')
        print('*' * 75)
        print('Executing %s ... Hit Ctrl+d when you are done, to return mfcloud.' % shell)
        print('*' * 75 + '\n')
        os.system(shell)

    cmd = subparsers.add_parser('sh', help='Fetch logs from containers')
    cmd.set_defaults(func=exec_bash)

    cmd = subparsers.add_parser('volumes', help='Show volumes of current project')
    cmd.add_argument('services', help='Service names', nargs='*')
    cmd.add_argument('--json', action='store_true', default=False)
    cmd.set_defaults(func='list_volumes')

    cmd = subparsers.add_parser('volume-push', help='Push volume to remote server')
    cmd.add_argument('volumes', help='Volume specs', nargs='*')
    cmd.set_defaults(func='push_volumes')

    cmd = subparsers.add_parser('volume-pull', help='Push volume to remote server')
    cmd.add_argument('volumes', help='Volume specs', nargs='*')
    cmd.set_defaults(func='pull_volumes')

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

    # mfcloud use ubuntu@myserver.com
    use_cmd = subparsers.add_parser('use', help='Sets target hostname')
    use_cmd.add_argument('host', help='Hostname with username ex. user@some.server')
    use_cmd.set_defaults(func='use_host')

    # mfcloud app create myapp
    app_create_cmd = subparsers.add_parser('@', help='Executes remote command')
    app_create_cmd.add_argument('command', help='Name of application', nargs='*')
    app_create_cmd.set_defaults(func='remote')

    class foo(Cmd):

        intro = '''
            __      _                 _
 _ __ ___  / _| ___| | ___  _   _  __| |
| '_ ` _ \| |_ / __| |/ _ \| | | |/ _` |
| | | | | |  _| (__| | (_) | |_| | (_| |
|_| |_| |_|_|  \___|_|\___/ \__,_|\__,_|

Cloud that loves your data.

'''

        def update_prompt(self):
            if os.path.exists('mfcloud.yml'):
                project = project_name_by_dir()
            else:
                project = '~'

            self.prompt = '(%s:%s) ' % (project, env.host_string or '~')


        def __init__(self, completekey='tab', stdin=None, stdout=None):

            self.client = MfcloudDeployment()
            self.client.init(os.getcwd(), 'dev')

            self.update_prompt()
            Cmd.__init__(self, completekey, stdin, stdout)

        def completedefault(self, *ignored):
            return Cmd.completedefault(self, *ignored)


        def exec_argparse(self, args):
            args = arg_parser.parse_args(args=args)
            args.argv0 = argv[0]
            if isinstance(args.func, str):
                getattr(self.client, args.func)(**vars(args))
            else:
                args.func(**vars(args))

        def onecmd(self, line):
            try:
                # reset project config
                self.client._project = None

                if line.strip() != '':
                    args = shlex.split(line.strip())
                    if args[0] == 'EOF':
                        if confirm('\nCtrl+d. Exit?', True):
                            return True
                    if args[0] in ('docker', 'ls', 'll', 'l', 'git'):
                        os.system(' '.join(args))
                    else:
                        self.exec_argparse(args)
                else:
                    arg_parser.print_help()
            except KeyboardInterrupt as e:
                print('Ctrl+c. Task interrupted.')
            except SystemExit as e:
                pass
            except Exception as e:
                print('Error: %s' % str(e))

            self.update_prompt()

    if len(argv) > 1:
        foo().exec_argparse(argv[1:])
    else:
        if not os.path.exists('mfcloud.yml'):
            if not confirm('Directory do not contain mfcloud.yml, mfcloud may be not so useful, continue to mfcloud?', False):
                raise SystemExit(0)
        foo().cmdloop()





def entry_point():
    """Zero-argument entry point for use with setuptools/distribute."""
    raise SystemExit(main(sys.argv))


if __name__ == '__main__':
    entry_point()
