from binascii import crc32
from tempfile import NamedTemporaryFile
from autobahn.twisted.util import sleep
from mfcloud.sync.utils import unarchive
import os
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks
from twisted.protocols.basic import FileSender
from twisted.python import log


class CrcCheckFailed(ValueError):
    pass


class TransferCancelled(Exception):
    """ Exception for a user cancelling a transfer """
    pass


class FileUploaderTarget(object):
    class Status(object):
        """ Status object.. just a demo """

        def update(self, **kargs):
            pass

    def __init__(self, protocol, base_dir, expected_crc):
        super(FileUploaderTarget, self).__init__()

        self.protocol = protocol
        self.base_dir = base_dir
        self.outfile = None
        self.outfilename = None
        self.remain = None
        self.size = None
        self.crc = 0
        self.expected_crc = expected_crc

    def start_upload(self, size):
        self.size = int(size)

        self.outfile = NamedTemporaryFile(delete=False)

        self.remain = size
        self.protocol.setRawMode()

    @inlineCallbacks
    def extract(self):
        try:
            if self.crc != self.expected_crc:
                yield self.protocol.transport.write('crc\r\n')
                yield sleep(0.1)
            else:
                yield threads.deferToThread(unarchive, self.base_dir, self.outfile.name)
                yield self.protocol.transport.write('ok\r\n')

            os.unlink(self.outfile.name)
            self.outfile = None
        except:
            log.err()

        self.protocol.transport.loseConnection()

    def raw_data(self, data):
        self.remain -= len(data)

        self.crc = crc32(data, self.crc)
        self.outfile.write(data)

        if self.remain == 0:
            self.extract()


    def stop(self, reason):
        if self.outfile:
            self.outfile.close()

        if hasattr(self.protocol.factory, 'controller'):
            self.protocol.factory.controller.completed.callback(None)


class FileUploaderSource(object):
    def __init__(self, path, controller, protocol):
        super(FileUploaderSource, self).__init__()
        self.protocol = protocol
        self.path = path
        self.controller = controller

        self.infile = open(self.path, 'rb')
        self.insize = os.stat(self.path).st_size

        self.result = None
        self.completed = False

        self.wait_result = False

        self.controller.file_sent = 0
        self.controller.file_size = self.insize

    def start(self):
        sender = FileSender()
        sender.CHUNK_SIZE = 2 ** 16
        d = sender.beginFileTransfer(self.infile, self.protocol.transport, self._monitor)
        d.addCallback(self.cbTransferCompleted)

    def lineReceived(self, line):
        if line.strip() == 'ok':
            self.controller.completed.callback('ok')
        elif line.strip() == 'crc':
            self.controller.completed.errback(CrcCheckFailed())
        else:
            self.controller.completed.errback(Exception('Unknown error: %s' % line))

    def stop(self, reason):
        self.infile.close()

        if not self.controller.completed.called:
            self.controller.completed.callback('ok')

    def _monitor(self, data):
        """ """
        self.controller.file_sent += len(data)
        self.controller.total_sent += len(data)

        # Check with controller to see if we've been cancelled and abort
        # if so.
        if self.controller.cancel:
            # Need to unregister the producer with the transport or it will
            # wait for it to finish before breaking the connection
            self.protocol.transport.unregisterProducer()
            self.protocol.transport.loseConnection()

            # Indicate a user cancelled result
            self.result = TransferCancelled('User cancelled transfer')

        return data

    def cbTransferCompleted(self, lastsent):
        """ """
        # self.completed = True
        # self.protocol.transport.loseConnection()

        self.protocol.setLineMode()

