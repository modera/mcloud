



class FileIOProtocol(basic.LineReceiver):
    """ File Receiver """
    app_controller = inject.attr(ApplicationController)
    """
    @type app_controller: ApplicationController
    """
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

        tar = yield threads.deferToThread(archive, resolved_path, data['paths'])

        crc = file_crc(tar)

        out_data = {
            'cmd': 'upload',
            'file_size': os.path.getsize(tar),
            'file_crc': crc
        }
        self.transport.write(json.dumps(out_data) + '\r\n')
        controller = type('test', (object,), {'cancel': False, 'total_sent': 0, 'completed': Deferred()})
        self.processor = FileUploaderSource(tar, controller, self)
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

