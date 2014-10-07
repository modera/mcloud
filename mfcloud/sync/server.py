import json
from shutil import rmtree
from mfcloud.sync.utils import archive, file_crc
import os
import inject
from mfcloud.application import ApplicationController
from mfcloud.events import EventBus
from mfcloud.sync.diff import directory_snapshot
from mfcloud.sync.transfer import FileUploaderTarget, FileUploaderSource
from twisted.internet import threads, reactor
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.protocol import ServerFactory
from twisted.protocols import basic
from twisted.python import log



class FileIOProtocol(basic.LineReceiver):
    """ File Receiver """
    app_controller = inject.attr(ApplicationController)
    """
    @type app_controller: ApplicationController
    """
    event_bus = inject.attr(EventBus)

    read_len = 0
    read_clb = None
    read_data = None

    class Session(object):
        """ Session object, just a demo """

        def is_invalid(self):
            return False

        def is_stale(self):
            return False

    def __init__(self):
        """ """
        self.session = FileIOProtocol.Session()
        self.outfile = None
        self.remain = 0

        self.processor = None

    def resolve_file_path(self, **kwargs):
        return self.factory.file_resolver.get_volume_path(**kwargs)


        # app = yield self.app_controller.get(app_name)
        # config = yield app.load()
        #
        # services = config.get_services()
        # service = services['%s.%s' % (service_name, app_name)]
        #
        # all_volumes = service.list_volumes()
        # if not volume in all_volumes:
        #     raise Exception('Volume with name %s no found!' % volume)
        #
        # defer.returnValue(os.path.join(all_volumes[volume], path))

    def _read(self, len):
        self.read_clb = Deferred()
        self.read_len = len
        self.read_data = ''

        return self.read_clb


    @inlineCallbacks
    def do_upload(self, data):
        path = yield self.resolve_file_path(**data['ref'])
        yield self.transport.write('go\r\n')
        self.processor = FileUploaderTarget(self, path, data['file_crc'])
        self.processor.start_upload(data['file_size'])

    @inlineCallbacks
    def do_snapshot(self, data):
        file_path = yield self.resolve_file_path(**data['args'])
        snapshot = directory_snapshot(file_path)

        self.transport.write(json.dumps(snapshot) + '\r\n')
        self.transport.loseConnection()

    @inlineCallbacks
    def do_remove(self, data):
        path = yield self.resolve_file_path(**data['args']['ref'])
        file_path = os.path.join(path, data['args']['path'])

        if os.path.isdir(file_path):
            rmtree(file_path, ignore_errors=True)
        else:
            os.unlink(file_path)

        self.transport.write(json.dumps(True) + '\r\n')
        self.transport.loseConnection()

    @inlineCallbacks
    def do_mkdir(self, data):
        path = yield self.resolve_file_path(**data['args']['ref'])
        file_path = os.path.join(path, data['args']['path']).decode('utf-8')
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        self.transport.write(json.dumps(True) + '\r\n')
        self.transport.loseConnection()


    @inlineCallbacks
    def do_download(self, data):
        resolved_path = yield self.resolve_file_path(**data['ref'])

        self.setRawMode()

        paths = yield self._read(data['paths_len'])
        paths = json.loads(paths)

        log.msg('Creating file archive')
        print('Archiving')
        tar = yield threads.deferToThread(archive, resolved_path, paths)


        crc = file_crc(tar)

        out_data = {
            'cmd': 'upload',
            'file_size': os.path.getsize(tar),
            'file_crc': crc
        }

        print('Initiating file transfer. %s MB' % (out_data['file_size'] / (1024 * 1024)))

        self.transport.write(json.dumps(out_data) + '\r\n')
        controller = type('test', (object,), {'cancel': False, 'total_sent': 0, 'completed': Deferred()})
        self.processor = FileUploaderSource(tar, controller, self)
        self.processor.start()

        yield controller.completed

        print('File transfer completed.')

    @inlineCallbacks
    def handle_msg(self, data):

        log.msg(data)

        try:
            if data['cmd'] == 'upload':
                yield self.do_upload(data)

            elif data['cmd'] == 'snapshot':
                yield self.do_snapshot(data)

            elif data['cmd'] == 'remove':
                yield self.do_remove(data)

            elif data['cmd'] == 'mkdir':
                yield self.do_mkdir(data)

            elif data['cmd'] == 'download':
                yield self.do_download(data)
            else:
                self.transport.write('err: Unknown command: %s' % data['cmd'] + '\r\n')
                self.transport.loseConnection()

        except Exception as e:
            log.err()
            self.transport.write('err: %s\r\n' % str(e.message))
            self.transport.loseConnection()


    def lineReceived(self, line):
        """ """
        try:
            data = json.loads(line)
        except ValueError:
            """
            Seems to be JSON is not valid, there. Most likely its "ok" or "crc"
            messages from client - we DON't need to react anyhow.
            """
            return

        # client=self.transport.getPeer().host

        self.handle_msg(data)


    def rawDataReceived(self, data):

        if self.read_len > 0:
            self.read_data += data
            self.read_len -= len(data)

            if self.read_len < 1:
                self.read_clb.callback(self.read_data)
        else:
            self.processor.raw_data(data)

    def connectionMade(self):
        """ """
        basic.LineReceiver.connectionMade(self)

    def connectionLost(self, reason):
        """ """

        if self.read_len > 0:
            self.read_clb.errback('Not all data recieved')

        basic.LineReceiver.connectionLost(self, reason)

        if self.processor:
            self.processor.stop(reason)


class FileIOFactory(ServerFactory):
    """ file receiver factory """
    protocol = FileIOProtocol

    noisy = False

    def __init__(self, file_resolver=None):
        """ """
        self.file_resolver = file_resolver



class FileServer(object):

    def __init__(self, host='0.0.0.0', port=7081, file_resolver=None):
        super(FileServer, self).__init__()
        self.host = host
        self.port = port
        self.file_resolver = file_resolver
        self.fileio = None
        self.connect = None

    def bind(self):
        self.fileio = FileIOFactory(file_resolver=self.file_resolver)
        self.connect = reactor.listenTCP(self.port, self.fileio)

    def stop(self):
        if self.connect:
            self.connect.stopListening()

