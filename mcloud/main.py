import logging
import sys
import signal

from bashutils.colors import color_text
import inject
from mcloud.interrupt import InterruptManager
from mcloud.remote import TaskFailure

from mcloud.rpc_client import arg_parser, ApiRpcClient, ClientProcessInterruptHandler
from mcloud.shell import mcloud_shell
from confire import Configuration
from twisted.internet import reactor
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

    if len(argv) < 2:
        # Use the tab key for completion

        # log.startLogging(open('twisted.log', 'w'))

        mcloud_shell()
        reactor.run()
    else:


        args = arg_parser.parse_args()

        if args.verbose:
            log.startLogging(sys.stdout)

        args.argv0 = argv[0]

        if isinstance(args.func, str):

            log.msg('Starting task: %s' % args.func)

            @inlineCallbacks
            def call_command():
                client = ApiRpcClient(host=args.host or '127.0.0.1', settings=settings)
                interrupt_manager.append(ClientProcessInterruptHandler(client))

                try:
                    yield getattr(client, args.func)(**vars(args))
                except Exception as e:
                    print '\n  %s\n' % color_text('%s: %s' % (type(e), str(e)), color='yellow')

                interrupt_manager.manual_interrupt()

            call_command()
            reactor.run()



        else:
            args.func(**vars(args))


def entry_point():
    """Zero-argument entry point for use with setuptools/distribute."""
    raise SystemExit(main(sys.argv))


if __name__ == '__main__':
    entry_point()

