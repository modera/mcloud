""" file: filesender.py

    Adapted from: Steven Wang's <steven.zdwang at gmail.com> post at:
          http://twistedmatrix.com/pipermail/twisted-python/2007-July/015738.html

    Usage: filesender.py [options]
       Options:
         -h, --help         show this help message and exit
         --port=PORT        Which port to use. (default "1234")
         --address=ADDRESS  Which address to use. (default "localhost")
         --server           Use server
         --client           Use client

    Examples:

      filesender.py --server <upload_save_directory>
      filesender.py --client <file_to_send>

    Example Output:

      Server:
                shell$ python ~/code/filesender.py --server --port 1234 /tmp
                    Listening on port 1234 ..

                     + a connection was made
                     *  IPv4Address(TCP, '127.0.0.1', 44621)
                     ~ lineReceived:
                            {"original_file_path": "/home/matt/Videos/hutter-ai.avi", "file_size": 218266926}
                     * Using upload dir: /tmp
                     * Receiving into file@ /tmp/data.out
                     & Entering raw mode. <open file '/tmp/data.out', mode 'wb' at 0x1fb01c8> 218266926
                     - connectionLost

                    --> finished saving upload@/tmp/data.out
                    --------------------------------------------------------------------------------
                    {'client': '127.0.0.1',
                     'crc': 1713872441,
                     'file_metadata': ' RIFF (little-endian) data, AVI, 720 x 480, ~30 fps, video',
                     'file_size': 218266926,
                     'new_file': '/tmp/data.out',
                     'original_file': u'/home/matt/Videos/hutter-ai.avi',
                     'upload_time': datetime.datetime(2010, 10, 16, 22, 27, 18, 683145)}

      Client:
                shell$ python ~/code/filesender.py --client ~/Videos/hutter.avi
                    + building protocol
                    - connectionLost
                     *  Connection was closed cleanly.
                    * finished with /home/matt/Videos/hutter-ai.avi

"""

from binascii import crc32
from optparse import OptionParser
from shutil import copy, rmtree
import sys
import os, json, pprint, datetime
import inject
from twisted.python import log
from mfcloud.events import EventBus
from mfcloud.application import ApplicationController

from twisted.protocols import basic
from twisted.internet import protocol
from twisted.application import service, internet
from twisted.internet.protocol import ServerFactory
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import FileSender
from twisted.internet import defer
from twisted.internet.defer import Deferred, inlineCallbacks
from twisted.internet import reactor
from mfcloud.volumes import directory_snapshot


pp = pprint.PrettyPrinter(indent=1)


class TransferCancelled(Exception):
    """ Exception for a user cancelling a transfer """
    pass

class FileUploaderTarget(object):

    class Status(object):
        """ Status object.. just a demo """

        def update(self, **kargs):
            """ """
            print '-' * 80
            pp.pprint(kargs)

    def __init__(self, protocol, base_dir):
        super(FileUploaderTarget, self).__init__()

        self.protocol = protocol
        self.base_dir = base_dir
        self.outfile = None
        self.outfilename = None
        self.remain = None
        self.size = None
        self.crc = 0


    def start_upload(self, file_path, size, ticket_id=None):
        self.size = int(size)

        print '-----'
        print self.base_dir
        print ticket_id
        print file_path
        print '-----'
        self.outfilename = os.path.join(self.base_dir, str(ticket_id), file_path)

        uploaddir = os.path.dirname(self.outfilename)
        if not os.path.exists(uploaddir):
            os.makedirs(uploaddir)

        print ' * Receiving into file@', self.outfilename
        try:
            self.outfile = open(self.outfilename, 'wb')
        except Exception, value:
            print ' ! Unable to open file', self.outfilename, value
            self.protocol.transport.loseConnection()
            return

        print '[[[[[ %d ]]]]]' % size
        self.remain = size
        print ' & Entering raw mode.', self.outfile, self.remain
        self.protocol.setRawMode()

    def raw_data(self, data):
        if self.remain % 10000 == 0:
            print '   & ', self.remain, '/', self.size
        self.remain -= len(data)

        self.crc = crc32(data, self.crc)
        self.outfile.write(data)

    def stop(self, reason):
        print ' - connectionLost'
        if self.outfile:
            self.outfile.close()

        # print self.outfilename
        print '>>%s<<' % self.outfilename ## open(self.outfilename).read()

        # Problem uploading - tmpfile will be discarded
        if self.remain != 0:
            print str(self.remain) + ')!=0'
            remove_base = '--> removing tmpfile@'
            if self.remain < 0:
                reason = ' .. file moved too much'
            if self.remain > 0:
                reason = ' .. file moved too little'

            if self.outfilename:
                print remove_base + self.outfilename + reason
                os.remove(self.outfilename)
            else:
                pass

        # Success uploading - tmpfile will be saved to disk.
        else:
            print '\n--> finished saving upload@' + self.outfilename

            if hasattr(self.protocol.factory, 'controller'):
                self.protocol.factory.controller.completed.callback(None)
            # self.status.update(crc=self.crc,
            #                    file_size=self.size,
            #                    new_file=self.outfilename,
            #                    upload_time=datetime.datetime.now())


class FileIOProtocol(basic.LineReceiver):
    """ File Receiver """


    """
    @type app_controller: ApplicationController
    """
    app_controller = inject.attr(ApplicationController)
    event_bus = inject.attr(EventBus)

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

    def resolve_file_path(self, path, app_name, service_name=None, volume=None):
        return self.factory.file_resolver(path=path, app_name=app_name, service_name=service_name, volume=volume)


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


    def remove_files(self, files):
        pass

    def lineReceived(self, line):
        """ """
        data = json.loads(line)
        # client=self.transport.getPeer().host

        if data['cmd'] == 'upload':
            self.processor = FileUploaderTarget(self, self.factory.basedir)
            self.processor.start_upload(data['path'], data['file_size'], ticket_id=data['ticket_id'])
            return

        elif data['cmd'] == 'download':

            file_path = self.resolve_file_path(data['path'], data['app_name'], data['service_name'], data['volume'])

            out_data = {
                'cmd': 'upload',
                'path': data['path'],
                'file_size': os.path.getsize(file_path),
                'ticket_id': data['ticket_id']
            }
            self.transport.write(json.dumps(out_data) + '\r\n')

            controller = type('test', (object,), {'cancel': False, 'snap_id': data['ticket_id'], 'total_sent': 0, 'completed': Deferred()})
            self.processor = FileUploaderSource(file_path, controller, self)
            self.processor.start()
            return

        else:
            raise Exception('Unknown command: %s' % data['cmd'])

        # # Never happens.. just a demo.
        # if self.session.is_invalid():
        #     print 'FileIOProtocol:lineReceived Invalid session'
        #     self.transport.loseConnection()
        #     return
        #
        # # Never happens.. just a demo.
        # if self.session.is_stale():
        #     print 'FileIOProtocol:lineReceived Stale session'
        #     self.transport.loseConnection()
        #     return


    def rawDataReceived(self, data):
        self.processor.raw_data(data)

    def connectionMade(self):
        """ """
        basic.LineReceiver.connectionMade(self)
        print '\n + a connection was made to server'
        print ' * ', self.transport.getPeer()

    def connectionLost(self, reason):
        """ """
        print('Losstttttt!')
        basic.LineReceiver.connectionLost(self, reason)
        if self.processor:
            self.processor.stop(reason)


def fileinfo(fname):
    """ when "file" tool is available, return it's output on "fname" """
    return ( os.system('file 2> /dev/null') != 0 and \
             os.path.exists(fname) and \
             os.popen('file "' + fname + '"').read().strip().split(':')[1] )


class FileIOFactory(ServerFactory):
    """ file receiver factory """
    protocol = FileIOProtocol

    def __init__(self, basedir, file_resolver=None):
        """ """
        self.basedir = basedir
        self.file_resolver = file_resolver

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

        self.controller.file_sent = 0
        self.controller.file_size = self.insize

    def start(self):
        sender = FileSender()
        sender.CHUNK_SIZE = 2 ** 16
        d = sender.beginFileTransfer(self.infile, self.protocol.transport,
                                     self._monitor)
        d.addCallback(self.cbTransferCompleted)

    def stop(self, reason):

        print ' - connectionLost\n  * ', reason.getErrorMessage()
        print ' * finished with', self.path
        self.infile.close()
        if self.completed:
            self.controller.completed.callback(self.result)
        else:
            self.controller.completed.errback(reason)


    def _monitor(self, data):
        """ """
        self.controller.file_sent += len(data)
        self.controller.total_sent += len(data)

        # Check with controller to see if we've been cancelled and abort
        # if so.
        if self.controller.cancel:
            print 'FileIOClient._monitor Cancelling'

            # Need to unregister the producer with the transport or it will
            # wait for it to finish before breaking the connection
            self.protocol.transport.unregisterProducer()
            self.protocol.transport.loseConnection()

            # Indicate a user cancelled result
            self.result = TransferCancelled('User cancelled transfer')

        return data

    def cbTransferCompleted(self, lastsent):
        """ """
        self.completed = True
        self.protocol.transport.loseConnection()


class FileIOUploaderClientProtocol(basic.LineReceiver):
    """ file sender """

    def __init__(self, path, source_path, ticket_id):
        self.path = path
        self.source_path = source_path
        self.ticket_id = ticket_id


    def connectionMade(self):
        """ """
        # self.ptransport.write(instruction + '\r\n')

        log.msg('Bugabuga')

        data = {
            'cmd': 'upload',
            'path': self.path,
            'file_size': os.path.getsize(self.source_path),
            'ticket_id': self.ticket_id
        }
        self.transport.write(json.dumps(data) + '\r\n')

        self.processor = FileUploaderSource(self.source_path, self.factory.controller, self)
        self.processor.start()


    def connectionLost(self, reason):
        """
            NOTE: reason is a twisted.python.failure.Failure instance
        """
        from twisted.internet.error import ConnectionDone
        basic.LineReceiver.connectionLost(self, reason)
        self.processor.stop(reason)


class FileIODownloaderClient(basic.LineReceiver):
    """ file sender """

    def __init__(self, path, app_name, service_name, volume, ticket_id, basedir):
        self.path = path
        self.app_name = app_name
        self.service_name = service_name
        self.volume = volume
        self.ticket_id = ticket_id
        self.basedir = basedir
        self.processor = None

    def lineReceived(self, line):
        """ """
        data = json.loads(line)
        # client=self.transport.getPeer().host

        print data

        if data['cmd'] == 'upload':
            self.processor = FileUploaderTarget(self, self.basedir)
            self.processor.start_upload(data['path'], data['file_size'], ticket_id=data['ticket_id'])
            return
        else:
            raise Exception('Unknown command: %s' % data['cmd'])

    def connectionMade(self):
        data = {
            'cmd': 'download',
            'path': self.path,
            'app_name': self.app_name,
            'service_name': self.service_name,
            'volume': self.volume,
            'ticket_id': self.ticket_id
        }
        self.transport.write(json.dumps(data) + '\r\n')


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




class FileIOClientFactory(ClientFactory):
    """ file sender factory """
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


class FileServer(object):

    def __init__(self, basedir=None, host='0.0.0.0', port=7081, file_resolver=None):
        super(FileServer, self).__init__()
        self.basedir = basedir
        self.host = host
        self.port = port
        self.file_resolver = file_resolver

    def bind(self):
        fileio = FileIOFactory(self.basedir, file_resolver=self.file_resolver)
        reactor.listenTCP(self.port, fileio)


class FileClient(object):

    def __init__(self, basedir=None, host='0.0.0.0', port=7081):
        super(FileClient, self).__init__()
        self.basedir = basedir
        self.host = host
        self.port = port

    def upload(self, path, source_path, ticket_id):

        controller = type('test', (object,), {'cancel': False, 'snap_id': ticket_id, 'total_sent': 0, 'completed': Deferred()})

        protocol = FileIOUploaderClientProtocol(path, source_path, ticket_id)
        f = FileIOClientFactory(protocol, controller)
        reactor.connectTCP(self.host, self.port, f)

        return controller.completed

    def download(self, path, app_name, service_name=None, volume=None, ticket_id=None):
        controller = type('test', (object,), {'cancel': False, 'snap_id': ticket_id, 'total_sent': 0, 'completed': Deferred()})

        protocol = FileIODownloaderClient(path, app_name, service_name, volume, ticket_id, self.basedir)
        f = FileIOClientFactory(protocol, controller)
        reactor.connectTCP(self.host, self.port, f)

        return controller.completed

class VolumeStorageRemote(object):

    def __init__(self, rpc_client, app, service, volume, remote_path, remote_port):
        super(VolumeStorageRemote, self).__init__()

        self.app = app
        self.service = service
        self.volume = volume
        self.rpc_client = rpc_client

        self.last_snapshot_id = None

    @inlineCallbacks
    def get_snapshot(self):
        snap = yield self.rpc_client._remote_exec('volume_snapshot', self.app, self.service, self.volume)
        self.last_snapshot_id = snap['id_']
        del snap['id_']
        defer.returnValue(snap)

    def accept(self, path):
        pass

    def sync(self, volume_diff, source):
        pass


class VolumeStorageLocal(object):
    def __init__(self, path):
        super(VolumeStorageLocal, self).__init__()

        self.path = path

    def get_snapshot(self):
        return directory_snapshot(self.path)

    def sync(self, volume_diff, source):

        for path in volume_diff['new']:
            self.upload(os.path.join(source.path, path), path)

        for path in volume_diff['upd']:
            self.upload(os.path.join(source.path, path), path)

        for path in volume_diff['del']:
            self.remove(path)

    def upload(self, src, path):
        print 'U %s' % path
        real_path = os.path.join(self.path, path)

        if path.endswith('/'):
            if not os.path.exists(real_path):
                os.makedirs(real_path)
        else:
            if os.path.exists(real_path):
                self._remove_path(real_path)
            copy(src, real_path)

    def _remove_path(self, real_path):
        if os.path.isdir(real_path):
            rmtree(real_path)
        else:
            os.unlink(real_path)

    def remove(self, path):
        print 'D %s' % path
        real_path = os.path.join(self.path, path)
        if real_path.endswith('/'):
            real_path = real_path[0:-1]
        self._remove_path(real_path)

