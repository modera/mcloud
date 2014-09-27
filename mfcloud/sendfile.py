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
from tempfile import mkdtemp
from autobahn.twisted.util import sleep
from mfcloud.util import query_yes_no
import re
import os, json, pprint, datetime
import inject
from twisted.internet.base import BlockingResolver
from twisted.python import log
from mfcloud.events import EventBus
from mfcloud.application import ApplicationController, Application

from twisted.protocols import basic
from twisted.internet import protocol
from twisted.application import service, internet
from twisted.internet.protocol import ServerFactory
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import FileSender
from twisted.internet import defer
from twisted.internet.defer import Deferred, inlineCallbacks
from twisted.internet import reactor
from mfcloud.volumes import directory_snapshot, compare
from time import time

pp = pprint.PrettyPrinter(indent=1)


class TransferCancelled(Exception):
    """ Exception for a user cancelling a transfer """
    pass

class FileUploaderTarget(object):

    class Status(object):
        """ Status object.. just a demo """

        def update(self, **kargs):
            pass

    def __init__(self, protocol, base_dir):
        super(FileUploaderTarget, self).__init__()

        self.protocol = protocol
        self.base_dir = base_dir
        self.outfile = None
        self.outfilename = None
        self.remain = None
        self.size = None
        self.crc = 0


    def start_upload(self, file_path, size):
        self.size = int(size)

        self.outfilename = os.path.join(self.base_dir, file_path)

        uploaddir = os.path.dirname(self.outfilename)
        if not os.path.exists(uploaddir):
            os.makedirs(uploaddir)

        try:
            self.outfile = open(self.outfilename, 'wb')
        except Exception, value:
            self.protocol.transport.loseConnection()
            return

        self.remain = size
        self.protocol.setRawMode()

    def raw_data(self, data):
        # if self.remain % 10000 == 0:
        #     print '   & ', self.remain, '/', self.size

        self.remain -= len(data)

        self.crc = crc32(data, self.crc)
        self.outfile.write(data)

    def stop(self, reason):
        if self.outfile:
            self.outfile.close()

        if self.remain != 0:
            # print str(self.remain) + ')!=0'
            # remove_base = '--> removing tmpfile@'
            # if self.remain < 0:
            #     reason = ' .. file moved too much'
            # if self.remain > 0:
            #     reason = ' .. file moved too little'

            if self.outfilename:
                # print remove_base + self.outfilename + reason
                os.remove(self.outfilename)
            else:
                pass

        # Success uploading - tmpfile will be saved to disk.
        else:
            # print '\n--> finished saving upload@' + self.outfilename

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

    @inlineCallbacks
    def do_upload(self, data):
        path = yield self.resolve_file_path(**data['ref'])
        self.processor = FileUploaderTarget(self, path)
        self.processor.start_upload(data['path'], data['file_size'])
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
        os.unlink(file_path)
        self.transport.write(json.dumps(True) + '\r\n')
        self.transport.loseConnection()

    @inlineCallbacks
    def do_mkdir(self, data):
        path = yield self.resolve_file_path(**data['args']['ref'])
        file_path = os.path.join(path, data['args']['path'])
        os.makedirs(file_path)
        self.transport.write(json.dumps(True) + '\r\n')
        self.transport.loseConnection()

    @inlineCallbacks
    def do_download(self, data):
        resolved_path = yield self.resolve_file_path(**data['ref'])
        file_path = os.path.join(resolved_path, data['path'])
        out_data = {
            'cmd': 'upload',
            'path': data['path'],
            'file_size': os.path.getsize(file_path)
        }
        self.transport.write(json.dumps(out_data) + '\r\n')
        controller = type('test', (object,), {'cancel': False, 'total_sent': 0, 'completed': Deferred()})
        self.processor = FileUploaderSource(file_path, controller, self)
        self.processor.start()

    def lineReceived(self, line):
        """ """
        data = json.loads(line)
        # client=self.transport.getPeer().host

        if data['cmd'] == 'upload':
            self.do_upload(data)

        elif data['cmd'] == 'snapshot':
            self.do_snapshot(data)

        elif data['cmd'] == 'remove':
            self.do_remove(data)

        elif data['cmd'] == 'mkdir':
            self.do_mkdir(data)

        elif data['cmd'] == 'download':
            self.do_download(data)
        else:
            self.transport.write('Unknown command: %s' % data['cmd'] + '\r\n')
            self.transport.loseConnection()


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

    def connectionLost(self, reason):
        """ """
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

    def __init__(self, file_resolver=None):
        """ """
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

    def __init__(self, path, source_path, ref):
        self.path = path
        self.source_path = source_path
        self.ref = ref

        self.processor = None


    def connectionMade(self):
        """ """
        # self.ptransport.write(instruction + '\r\n')

        path = os.path.join(self.source_path, self.path)

        data = {
            'cmd': 'upload',
            'path': self.path,
            'ref': self.ref,
            'file_size': os.path.getsize(path)
        }
        self.transport.write(json.dumps(data) + '\r\n')

        self.processor = FileUploaderSource(path, self.factory.controller, self)
        self.processor.start()


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

    def __init__(self, path, target_path, ref):
        self.path = path
        self.target_path = target_path
        self.ref = ref
        self.processor = None

    def lineReceived(self, line):
        """ """
        data = json.loads(line)
        # client=self.transport.getPeer().host

        if data['cmd'] == 'upload':
            self.processor = FileUploaderTarget(self, self.target_path)
            self.processor.start_upload(data['path'], data['file_size'])
            return
        else:
            raise Exception('Unknown command: %s' % data['cmd'])

    def connectionMade(self):
        data = {
            'cmd': 'download',
            'path': self.path,
            'ref': self.ref
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


class FileClient(object):

    def __init__(self, host='0.0.0.0', port=7081):
        super(FileClient, self).__init__()
        self.port = port
        self.host = host

    def upload(self, path, source_path, **kwargs):

        controller = type('test', (object,), {'cancel': False, 'total_sent': 0, 'completed': Deferred()})

        protocol = FileIOUploaderClientProtocol(path, source_path, kwargs)
        f = FileIOClientFactory(protocol, controller)
        reactor.connectTCP(self.host, self.port, f, timeout=2)

        return controller.completed

    def download(self, path, target_path, **kwargs):
        controller = type('test', (object,), {'cancel': False, 'total_sent': 0, 'completed': Deferred()})

        protocol = FileIODownloaderClient(path, target_path, kwargs)
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


def _remove_path(real_path):
    if os.path.isdir(real_path):
        rmtree(real_path)
    else:
        os.unlink(real_path)

class VolumeStorageRemote(object):
    def __init__(self, host, port, **ref):
        super(VolumeStorageRemote, self).__init__()

        self.ref = ref
        for key, val in ref.items():
            if val is None:
                del ref[key]

        if host == 'me':
            host = 'localhost'

        self.host = host
        self.port = port

        self.last_snapshot_id = None

    def _get_client(self):
        return FileClient(host=self.host, port=self.port)

    def get_snapshot(self):
        return self._get_client().snapshot(**self.ref)

    def upload(self, path, base_dir):
        if path.endswith('/'):
            return self._get_client().mkdir(path=path, **self.ref)
        else:
            return self._get_client().upload(path, base_dir, **self.ref)

    def download(self, path, base_dir):
        target_path = os.path.join(base_dir, path)

        if path.endswith('/'):
            if not os.path.exists(target_path):
                os.makedirs(target_path)
        else:
            if not os.path.exists(os.path.dirname(target_path)):
                os.makedirs(target_path)

            if os.path.exists(target_path):
                _remove_path(target_path)

            return self._get_client().download(path, base_dir, **self.ref)

    def remove(self, path):
        return self._get_client().remove(path=path, **self.ref)




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

    def _do_copy(self, src_path, target_path):

        if target_path.endswith('/'):
            if not os.path.exists(target_path):
                os.makedirs(target_path)
        else:
            if not os.path.exists(os.path.dirname(target_path)):
                os.makedirs(target_path)

            if os.path.exists(target_path):
                _remove_path(target_path)

            copy(src_path, target_path)

    def download(self, path, base_dir):
        src_path = os.path.join(self.path, path)
        target_path = os.path.join(base_dir, path)

        self._do_copy(src_path, target_path)

    def upload(self, path, base_dir):
        target_path = os.path.join(self.path, path)
        src_path = os.path.join(base_dir, path)

        self._do_copy(src_path, target_path)

    def remove(self, path):
        real_path = os.path.join(self.path, path)
        if real_path.endswith('/'):
            real_path = real_path[0:-1]
        _remove_path(real_path)


def get_storage(ref):
    match = re.match('^((%(app_regex)s)\.)?(%(service_regex)s)@([a-z0-9A-Z\-\.]+)(:([0-9]+))?(:(.*))?$' % {
        'app_regex': Application.APP_REGEXP,
        'service_regex': Application.SERVICE_REGEXP,
    }, ref)
    if match:
        service = match.group(2)
        app = match.group(3)
        host = match.group(4)
        port = match.group(6) or 7081
        port = int(port)
        volume = match.group(8)

        # if not re.match('^[0-9\.]+$', host):
        #     host = BlockingResolver().getHostByName(host)

        return VolumeStorageRemote(host, port, app_name=app, service=service, volume=volume)
    else:
        return VolumeStorageLocal(ref)


def print_diff(volume_diff):

    for type_, label in (('new', 'New'), ('upd', 'Updated'), ('del', 'Removed'), ):
        if volume_diff[type_]:
            print '\n'
            print '%s\n' % label + '-' * 40

            cnt = 0
            for file_ in volume_diff[type_]:
                print '   - ' + file_
                cnt += 1
                if cnt > 10:
                    print 'And %s files more ...' % (len(volume_diff[type_]) - 11)
                    break

            has_changes = True

def diff_has_changes(volume_diff):
    return volume_diff['new'] or volume_diff['upd'] or volume_diff['del']

@inlineCallbacks
def storage_sync(src, dst, confirm=False, verbose=False, remove=False):

    start = time()

    if verbose:
        print('Calculating volume differences')

    snapshot_src = yield src.get_snapshot()
    if verbose:
        print('.')

    snapshot_dst = yield dst.get_snapshot()


    if verbose:
        print('.')

    volume_diff = compare(snapshot_src, snapshot_dst, drift=(time() - start))

    if not remove:
        volume_diff['del'] = []

    if not diff_has_changes(volume_diff):
        print('Files are in sync already.')
        return

    if confirm:
        print_diff(volume_diff)
        if not query_yes_no('Apply changes?', default='no'):
            return

    paths_to_upload = volume_diff['new'] + volume_diff['upd']

    if len(paths_to_upload):
        tmp_path = mkdtemp()

    try:
        if verbose:
            log.msg('Syncing ... ')

        for path in paths_to_upload:
            if verbose:
                print(path)
            yield src.download(path, tmp_path)
            yield dst.upload(path, tmp_path)

        for path in volume_diff['del']:
            yield dst.remove(path)
    finally:
        if len(paths_to_upload):
            rmtree(tmp_path)