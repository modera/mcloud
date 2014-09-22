
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
import sys
import os, json, pprint, datetime

from twisted.protocols import basic
from twisted.internet import protocol
from twisted.application import service, internet
from twisted.internet.protocol import ServerFactory
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import FileSender
from twisted.internet.defer import Deferred
from twisted.internet import reactor

pp = pprint.PrettyPrinter(indent=1)

class TransferCancelled(Exception):
    """ Exception for a user cancelling a transfer """
    pass

class FileIOProtocol(basic.LineReceiver):
    """ File Receiver """

    class Session(object):
        """ Session object, just a demo """
        def is_invalid(self):
            return False

        def is_stale(self):
            return False

    class Status(object):
        """ Status object.. just a demo """
        def update(self, **kargs):
            """ """
            print '-'*80
            pp.pprint(kargs)

    def __init__(self):
        """ """
        self.session = FileIOProtocol.Session()
        self.status = FileIOProtocol.Status()
        self.outfile = None
        self.remain = 0
        self.crc = 0

    def lineReceived(self, line):
        """ """
        print ' ~ lineReceived:\n\t', line
        self.instruction = json.loads(line)
        self.instruction.update(dict(client=self.transport.getPeer().host))
        self.size = self.instruction['file_size']
        self.original_fname = self.instruction.get('original_file_path',
                                                   'not given by client')
        # Never happens.. just a demo.
        if self.session.is_invalid():
            print 'FileIOProtocol:lineReceived Invalid session'
            self.transport.loseConnection()
            return

        # Never happens.. just a demo.
        if self.session.is_stale():
            print 'FileIOProtocol:lineReceived Stale session'
            self.transport.loseConnection()
            return

        # Create the upload directory if not already present
        uploaddir = file_path
        print " * Using upload dir:",uploaddir
        if not os.path.isdir(uploaddir):
            os.makedirs(uploaddir)

        self.outfilename = os.path.join(uploaddir, 'data.out')

        print ' * Receiving into file@',self.outfilename
        try:
            self.outfile = open(self.outfilename,'wb')
        except Exception, value:
            print ' ! Unable to open file', self.outfilename, value
            self.transport.loseConnection()
            return

        self.remain = int(self.size)
        print ' & Entering raw mode.',self.outfile, self.remain
        self.setRawMode()

    def rawDataReceived(self, data):
        """ """
        if self.remain%10000==0:
            print '   & ',self.remain,'/',self.size
        self.remain -= len(data)

        self.crc = crc32(data, self.crc)
        self.outfile.write(data)

    def connectionMade(self):
        """ """
        basic.LineReceiver.connectionMade(self)
        print '\n + a connection was made'
        print ' * ',self.transport.getPeer()

    def connectionLost(self, reason):
        """ """
        basic.LineReceiver.connectionLost(self, reason)
        print ' - connectionLost'
        if self.outfile:
            self.outfile.close()
        # Problem uploading - tmpfile will be discarded
        if self.remain != 0:
            print str(self.remain) + ')!=0'
            remove_base = '--> removing tmpfile@'
            if self.remain<0:
                reason = ' .. file moved too much'
            if self.remain>0:
                reason = ' .. file moved too little'
            print remove_base + self.outfilename + reason
            os.remove(self.outfilename)

        # Success uploading - tmpfile will be saved to disk.
        else:
            print '\n--> finished saving upload@' + self.outfilename
            client = self.instruction.get('client', 'anonymous')
            self.status.update( crc           = self.crc,
                                file_size     = self.size,
                                client        = client,
                                new_file      = self.outfilename,
                                original_file = self.original_fname,
                                file_metadata = fileinfo(self.outfilename),
                                upload_time   = datetime.datetime.now() )
def fileinfo(fname):
    """ when "file" tool is available, return it's output on "fname" """
    return ( os.system('file 2> /dev/null')!=0 and \
             os.path.exists(fname) and \
             os.popen('file "'+fname+'"').read().strip().split(':')[1] )


class FileIOFactory(ServerFactory):
    """ file receiver factory """
    protocol = FileIOProtocol

    def __init__(self, db, options={}):
        """ """
        self.db = db
        self.options = options


class FileIOClient(basic.LineReceiver):
    """ file sender """

    def __init__(self, path, controller):
        """ """
        self.path = path
        self.controller = controller

        self.infile = open(self.path, 'rb')
        self.insize = os.stat(self.path).st_size

        self.result = None
        self.completed = False

        self.controller.file_sent = 0
        self.controller.file_size = self.insize

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
            self.transport.unregisterProducer()
            self.transport.loseConnection()

            # Indicate a user cancelled result
            self.result = TransferCancelled('User cancelled transfer')

        return data

    def cbTransferCompleted(self, lastsent):
        """ """
        self.completed = True
        self.transport.loseConnection()

    def connectionMade(self):
        """ """
        instruction = dict(file_size=self.insize,
                           original_file_path=self.path)
        instruction = json.dumps(instruction)
        self.transport.write(instruction+'\r\n')
        sender = FileSender()
        sender.CHUNK_SIZE = 2 ** 16
        d = sender.beginFileTransfer(self.infile, self.transport,
                                     self._monitor)
        d.addCallback(self.cbTransferCompleted)

    def connectionLost(self, reason):
        """
            NOTE: reason is a twisted.python.failure.Failure instance
        """
        from twisted.internet.error import ConnectionDone
        basic.LineReceiver.connectionLost(self, reason)
        print ' - connectionLost\n  * ', reason.getErrorMessage()
        print ' * finished with',self.path
        self.infile.close()
        if self.completed:
            self.controller.completed.callback(self.result)
        else:
            self.controller.completed.errback(reason)
        reactor.stop()

class FileIOClientFactory(ClientFactory):
    """ file sender factory """
    protocol = FileIOClient

    def __init__(self, path, controller):
        """ """
        self.path = path
        self.controller = controller

    def clientConnectionFailed(self, connector, reason):
        """ """
        ClientFactory.clientConnectionFailed(self, connector, reason)
        self.controller.completed.errback(reason)

    def buildProtocol(self, addr):
        """ """
        print ' + building protocol'
        p = self.protocol(self.path, self.controller)
        p.factory = self
        return p


def transmitOne(path, address='localhost', port=1234,):
    """ helper for file transmission """
    controller = type('test',(object,),{'cancel':False, 'total_sent':0,'completed':Deferred()})
    f = FileIOClientFactory(path, controller)
    reactor.connectTCP(address, port, f)
    return controller.completed


def build_parser():
    """ builds the command line parser """
    parser = OptionParser()
    portHelp = 'Which port to use. (default "1234")'
    addressHelp = 'Which address to use. (default "localhost")'
    serverHelp = "Use server"
    clientHelp = "Use client"
    parser.add_option("--port", dest="port", default='1234', help=portHelp, metavar="PORT")
    parser.add_option("--address", dest="address", default='127.0.0.1', help=addressHelp, metavar="ADDRESS")
    parser.add_option("--server",action="store_true",default=False, dest="use_server",help=serverHelp)
    parser.add_option("--client",action="store_true",default=False, dest="use_client",help=clientHelp)
    return parser


parser = build_parser()
(options, args) = parser.parse_args()

file_arg = args[0]
file_path = file_arg

if __name__=='__main__':
    assert options.use_client or options.use_server,"Must specify client or server"
    assert options.port,'Must provide --port'
    port    = int(options.port)
    address  = options.address

    if options.use_client:
        if not file_arg:
            file_path = sys.argv[0]
        transmitOne(file_path,port=port,address=address)
        print 'Dialing on port',port,'..'
        reactor.run()

    if options.use_server:
        fileio = FileIOFactory({})
        reactor.listenTCP(port, fileio)
        print 'Listening on port',port,'..'
        reactor.run()