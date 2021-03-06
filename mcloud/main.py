import logging
import os
import sys
import signal
import traceback

from bashutils.colors import color_text
import inject
from mcloud.interrupt import InterruptManager
from mcloud.remote import TaskFailure

from mcloud.rpc_client import arg_parser, subparsers, ApiRpcClient, ClientProcessInterruptHandler
from mcloud.shell import mcloud_shell
from confire import Configuration
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks
from twisted.python import log


class ReactorInterruptHandler(object):

    def interrupt(self, last=None):
        reactor.callFromThread(reactor.stop)

def main(argv):
    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setFormatter(logging.Formatter())
    console_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)
    root_logger.debug('Logger initialized')

    logging.getLogger("requests").propagate = False

    class SslConfiguration(Configuration):
        enabled = False
        key = '/etc/mcloud/ssl.key'
        cert = '/etc/mcloud/ssl.crt'

    class MyAppConfiguration(Configuration):

        CONF_PATHS = [
            '/etc/mcloud/mcloud-client.yml',
            # os.path.expanduser('~/.myapp.yaml'),
            # os.path.abspath('conf/myapp.yaml')
        ]

        haproxy = False

        ssl = SslConfiguration()

    settings = MyAppConfiguration.load()

    interrupt_manager = InterruptManager()
    interrupt_manager.append(ReactorInterruptHandler())
    interrupt_manager.register_interupt_handler()

    def my_config(binder):
        binder.bind('settings', settings)
        binder.bind('interrupt_manager', interrupt_manager)

    # Configure a shared injector.
    inject.configure(my_config)

    # client = ApiRpcClient(host=args.host, settings=settings)
    # subparsers.add_parser('!booo', help='Deploy application')

    if len(argv) == 2 and ('shell' == argv[1] or '@' in argv[1]):
        mcloud_shell(argv[1] if '@' in argv[1] else None)
        reactor.run()

    elif len(argv) == 1:
        arg_parser.print_help()
        sys.exit(2)

    else:
        args = arg_parser.parse_args()

        if args.verbose:
            log.startLogging(sys.stdout)

        args.argv0 = argv[0]

        if isinstance(args.func, str):

            log.msg('Starting task: %s' % args.func)

            @inlineCallbacks
            def call_command():
                client = ApiRpcClient(host=args.host, settings=settings)
                interrupt_manager.append(ClientProcessInterruptHandler(client))

                try:
                    yield getattr(client, args.func)(**vars(args))
                except Exception as e:
                    label = type(e)
                    if isinstance(e, ValueError):
                        label = 'error'
                    else:
                        label = str(label)

                    print '\n  %s: %s\n' % (
                        color_text(label, color='cyan'),
                        color_text(str(e), color='yellow'),
                    )

                interrupt_manager.manual_interrupt()

            call_command()
            reactor.run()

        else:
            ret = args.func(**vars(args))

            if isinstance(ret, defer.Deferred):
                def clb(*args):
                    reactor.callFromThread(reactor.stop)
                ret.addCallback(clb)

                reactor.run()


def entry_point():
    """Zero-argument entry point for use with setuptools/distribute."""
    raise SystemExit(main(sys.argv))


if __name__ == '__main__':
    entry_point()

