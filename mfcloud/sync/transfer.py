from __future__ import print_function
from binascii import crc32
from tempfile import NamedTemporaryFile
import sys
from autobahn.twisted.util import sleep
from mfcloud.sync.utils import unarchive
import os
from twisted.internet import threads, task
from twisted.internet.defer import inlineCallbacks
from twisted.protocols.basic import FileSender
from twisted.python import log


class CrcCheckFailed(ValueError):
    pass


class TransferCancelled(Exception):
    """ Exception for a user cancelling a transfer """
    pass

class Monitor(object):
    def __init__(self):
        super(Monitor, self).__init__()

        self.last_remain = 0
        self.spinner = 0
        self.speed = 0
        self.remain = None
        self.size = None

    def tick(self, size, remian):
        self.size = size
        self.remain = remian

        self.print_stats()

    def format_measure(self, bytes_len):
        if bytes_len < 1024:
            bytes_len_unit = 'KB'
            bytes_len_measure = 1024.0
        else:
            bytes_len_unit = 'MB'
            bytes_len_measure = 1024.0 * 1024.0

        return '%s %s' % (round(bytes_len / bytes_len_measure, 2), bytes_len_unit)

    def print_stats(self):

        downloaded = self.size - self.remain
        percent = round((downloaded / float(self.size)) * 100, 0)

        sys.stdout.write('\r%s   Transfer %s%% (%s of %s). Speed: %s/s                                ' % (
            ('|', '/', '-', '\\')[self.spinner],
            percent,
            self.format_measure(downloaded),
            self.format_measure(self.size),
            self.format_measure(self.speed))
        )
        sys.stdout.flush()

        self.spinner += 1
        if self.spinner > 3:
            self.spinner = 0

            self.speed = self.last_remain - self.remain
            self.last_remain = self.remain



class FileUploaderTarget(object):
    class Status(object):
        """ Status object.. just a demo """

        def update(self, **kargs):
            pass

    def __init__(self, protocol, base_dir, expected_crc, monitor=None):
        super(FileUploaderTarget, self).__init__()

        self.protocol = protocol
        self.base_dir = base_dir
        self.outfile = None
        self.outfilename = None
        self.remain = None
        self.size = None
        self.crc = 0
        self.expected_crc = expected_crc

        self.loop = None
        self.monitor = monitor

    def monitor_loop(self):
        if self.monitor:
            self.monitor.tick(self.size, self.remain)

    def start_upload(self, size):
        self.size = int(size)

        self.outfile = NamedTemporaryFile(delete=False)

        self.remain = size
        self.last_remain = size

        if self.monitor:
            self.loop = task.LoopingCall(self.monitor_loop)
            self.loop.start(0.25)

        self.protocol.setRawMode()

    @inlineCallbacks
    def extract(self):
        log.msg('Transfer done. Extracting files.')
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

        if self.loop:
            self.loop.stop()

        if self.outfile:
            self.outfile.close()

        if hasattr(self.protocol.factory, 'controller'):
            if self.remain == 0:
                print('\nFile transfer done.')
                self.protocol.factory.controller.completed.callback(None)
            else:
                self.protocol.factory.controller.completed.errback(Exception('Still some date rmaining untransferred: %s' % self.remain))
        else:
            if not self.remain == 0:
                raise Exception('Still some date rmaining untranferred: %s' % self.remain)


class FileUploaderSource(object):
    def __init__(self, path, controller, protocol, monitor=None):
        super(FileUploaderSource, self).__init__()
        self.protocol = protocol
        self.path = path
        self.controller = controller

        self.infile = open(self.path, 'rb')
        self.insize = os.stat(self.path).st_size
        self.sent_size = 0

        self.result = None
        self.completed = False

        self.wait_result = False

        self.controller.file_sent = 0
        self.controller.file_size = self.insize

        self.loop = None
        self.monitor = monitor

    def monitor_loop(self):
        if self.monitor:
            self.monitor.tick(self.insize, self.insize - self.sent_size)


    def start(self):
        sender = FileSender()
        sender.CHUNK_SIZE = 2 ** 16
        d = sender.beginFileTransfer(self.infile, self.protocol.transport, self._monitor)
        d.addCallback(self.cbTransferCompleted)

        if self.monitor:
            self.loop = task.LoopingCall(self.monitor_loop)
            self.loop.start(0.25)

    def lineReceived(self, line):
        if line.strip() == 'ok':
            self.controller.completed.callback('ok')
        elif line.strip() == 'crc':
            self.controller.completed.errback(CrcCheckFailed())
        else:
            self.controller.completed.errback(Exception('Unknown error: %s' % line))

    def stop(self, reason):
        self.infile.close()

        if self.loop:
            self.loop.stop()

        if not self.controller.completed.called:
            self.controller.completed.callback('ok')

    def _monitor(self, data):
        """ """

        # if self.controller.total_sent > 0:
        #     print('%%%s' % (self.controller.file_size / self.controller.total_sent))

        self.sent_size += len(data)
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

