import json
from time import sleep
from mfcloud.sync.transfer import FileUploaderSource, FileUploaderTarget, Monitor
from mfcloud.sync.utils import file_crc, archive
import os
from twisted.internet import threads, reactor
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.protocol import ClientFactory
from twisted.protocols import basic
from twisted.python import log


class FileServerError(Exception):
    """
    Exception is thrown when volume can not be resolved.
    """

    pass

class FileIOUploaderClientProtocol(basic.LineReceiver):
    """ file sender """


    def __init__(self, path, crc, ref, monitor=None):
        self.path = path
        self.ref = ref
        self.crc = crc

        self.processor = None
        self.monitor = monitor

        self.downloading = False


    def connectionMade(self):
        """ """

        data = {
            'cmd': 'upload',
            'ref': self.ref,
            'file_size': os.path.getsize(self.path),
            'file_crc': self.crc,
        }
        self.transport.write(json.dumps(data) + '\r\n')

    def lineReceived(self, line):
        if not self.downloading and line.strip() == 'go':
            self.downloading = True
            self.processor = FileUploaderSource(self.path, self.factory.controller, self, monitor=self.monitor)
            self.processor.start()
        elif self.downloading and self.processor:
            self.processor.lineReceived(line)
        else:
            raise Exception('Unexpected data received: %s' % line)


    def connectionLost(self, reason):
        """
            NOTE: reason is a twisted.python.failure.Failure instance
        """
        from twisted.internet.error import ConnectionDone

        basic.LineReceiver.connectionLost(self, reason)

        if self.processor:
            self.processor.stop(reason)


class FileIODownloaderClient(basic.LineReceiver):
    """ file sender """

    def __init__(self, paths, target_path, ref, monitor=None):
        self.paths = paths
        self.target_path = target_path
        self.ref = ref
        self.processor = None
        self.monitor = monitor

    def lineReceived(self, line):
        """ """
        try:
            data = json.loads(line)
        except ValueError:
            log.err()
            return
        # client=self.transport.getPeer().host

        # if data['cmd'] == 'out':
        #     if self.monitor:
        #         self.monitor.out(data['msg'])

        if data['cmd'] == 'upload':

            self.processor = FileUploaderTarget(self, self.target_path, data['file_crc'], monitor=self.monitor)
            self.processor.start_upload(data['file_size'])
            return
        else:
            raise Exception('Unknown command: %s' % data['cmd'])

    def connectionMade(self):
        paths = json.dumps(self.paths)
        data = {
            'cmd': 'download',
            'paths_len': len(paths),
            'ref': self.ref
        }
        print('Preparing file archive ...')
        self.transport.write(json.dumps(data) + '\r\n')
        reactor.callLater(0.1, self.transport.write, paths)



    def rawDataReceived(self, data):
        self.processor.raw_data(data)

    def connectionLost(self, reason):
        """
            NOTE: reason is a twisted.python.failure.Failure instance
        """
        from twisted.internet.error import ConnectionDone

        basic.LineReceiver.connectionLost(self, reason)
        if self.processor:
            self.processor.stop(reason)


class FileIOCommandClient(basic.LineReceiver):
    """ file sender """

    def __init__(self, command, args):
        self.command = command
        self.args = args

        self.data = ''

    def rawDataReceived(self, data):
        self.data += data

    def connectionMade(self):
        data = {
            'cmd': self.command,
            'args': self.args
        }
        self.transport.write(json.dumps(data) + '\r\n')
        self.setRawMode()


    def connectionLost(self, reason):

        if self.data.startswith('err:'):
            self.factory.controller.completed.errback(FileServerError(self.data))
            return

        if self.data.endswith('\r\n'):
            self.data = self.data[0:-2]

        try:
            data_decoded = json.loads(self.data)

            self.factory.controller.completed.callback(data_decoded)
        except ValueError as e:
            print ('Incorrect data received: %s of len %d' % (self.data, len(self.data)))
            self.factory.controller.completed.errback(e)

        """
            NOTE: reason is a twisted.python.failure.Failure instance
        """
        from twisted.internet.error import ConnectionDone

        basic.LineReceiver.connectionLost(self, reason)


class FileIOClientFactory(ClientFactory):
    """ file sender factory """

    noisy = False

    def __init__(self, protocol, controller):
        """ """
        self.protocol = protocol
        self.controller = controller

    def startedConnecting(self, connector):
        ClientFactory.startedConnecting(self, connector)


    def clientConnectionFailed(self, connector, reason):
        """ """
        ClientFactory.clientConnectionFailed(self, connector, reason)
        self.controller.completed.errback(reason)

    def buildProtocol(self, addr):
        """ """
        p = self.protocol
        p.factory = self
        return p


class FileClient(object):
    def __init__(self, host='0.0.0.0', port=7081):
        super(FileClient, self).__init__()
        self.port = port
        self.host = host
        self.file_crc = file_crc

    @inlineCallbacks
    def upload(self, paths, source_path, **kwargs):
        if not isinstance(paths, list) and not isinstance(paths, tuple):
            paths = [paths]

        controller = type('test', (object,), {'cancel': False, 'total_sent': 0, 'completed': Deferred()})

        print('Creating archive')
        tar = yield threads.deferToThread(archive, source_path, paths)

        crc = self.file_crc(tar)

        # print tar

        protocol = FileIOUploaderClientProtocol(tar, crc, kwargs, monitor=Monitor())
        f = FileIOClientFactory(protocol, controller)
        reactor.connectTCP(self.host, self.port, f, timeout=2)

        yield controller.completed

        os.unlink(tar)


    def download(self, paths, target_path, **kwargs):
        if not isinstance(paths, list) and not isinstance(paths, tuple):
            paths = [paths]

        controller = type('test', (object,), {'cancel': False, 'total_sent': 0, 'completed': Deferred()})

        protocol = FileIODownloaderClient(paths, target_path, kwargs, monitor=Monitor())
        f = FileIOClientFactory(protocol, controller)
        reactor.connectTCP(self.host, self.port, f, timeout=2)

        return controller.completed

    def _exec_command(self, command, args):
        controller = type('test', (object,), {'cancel': False, 'snap_id': 0, 'total_sent': 0, 'completed': Deferred()})

        protocol = FileIOCommandClient(command, args)
        f = FileIOClientFactory(protocol, controller)
        reactor.connectTCP(self.host, self.port, f, timeout=4)

        return controller.completed

    def snapshot(self, **kwargs):
        return self._exec_command('snapshot', kwargs)

    def remove(self, path=None, **kwargs):
        return self._exec_command('remove', {
            'path': path,
            'ref': kwargs
        })

    def mkdir(self, path=None, **kwargs):
        return self._exec_command('mkdir', {
            'path': path,
            'ref': kwargs
        })

