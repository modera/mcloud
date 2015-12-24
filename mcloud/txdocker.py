from base64 import b64decode
import base64
import json
import logging
from urllib.parse import urlencode
import sys
from OpenSSL.crypto import PKey, FILETYPE_PEM, load_certificate, load_privatekey
from mcloud import txhttp
from mcloud.attach import Attach, AttachFactory, Terminal, AttachStdinProtocol

from mcloud.events import EventBus
from mcloud.remote import ApiRpcServer
import os
import inject
from mcloud.util import Interface
import re
from twisted.conch import stdio
from twisted.internet import defer, reactor
from twisted.internet._sslverify import Certificate, KeyPair
from twisted.internet.defer import inlineCallbacks
from twisted.internet.protocol import Protocol
from twisted.protocols import basic
from twisted.web._newclient import ResponseDone, ResponseFailed
from twisted.web.error import PageRedirect
from twisted.web.http import PotentialDataLoss

logger = logging.getLogger('mcloud.docker')

class IDockerClient(Interface):
    pass


def json_response(result):
    return txhttp.json_content(result)


class CommandFailed(Exception):
    pass

class NotFound(Exception):
    pass


class DockerConnectionFailed(Exception):
    pass


class DockerTwistedClient(object):

    DOCKER_API_VERSION = 'v1.19'

    rpc_server = inject.attr(ApiRpcServer)
    eb = inject.attr(EventBus)

    def versionize(self, url):
        return url + self.DOCKER_API_VERSION + '/'

    def task_log(self, ticket_id, message):
        self.rpc_server.task_progress(message, ticket_id)

    def task_stdout(self, ticket_id, data):
        self.rpc_server.task_stdout(data, ticket_id)

    def __init__(self, url=None, key=None, crt=None, ca=None):
        super(DockerTwistedClient, self).__init__()

        self.crt = crt
        self.key = key
        self.ca = ca

        if url is None:
            url = os.environ.get('DOCKER_API_URL', 'unix://var/run/docker.sock/')

        self.url = url + '/'

        logger.info('Connecting docker: %s' % self.url)

    def _request(self, url, method=txhttp.get, follow_redirects=1, **kwargs):

        if not '://' in url:
            url_ = '%s%s' % (self.versionize(self.url), url)
        else:
            url_ = url

        d = method(url_, timeout=30, key=self.key, crt=self.crt, ca=self.ca, **kwargs)

        def error(failure):
            if hasattr(failure.value, 'reasons'):
                reason = failure.value.reasons[0]
                redirect = reason.check(PageRedirect)

                if redirect:
                    if follow_redirects:
                        logger.error('Http redirect: %s' % reason.value.location)
                        return self._request(reason.value.location, method=method, follow_redirects=follow_redirects - 1, **kwargs)
                    else:
                        raise DockerConnectionFailed('Redirect from %s -> %s requested, but redirect limit exceed.' % (url_, reason.value.location))

            raise DockerConnectionFailed('Connection error: %s When connecting to: %s' % (failure.getErrorMessage(), url_))

        d.addErrback(error)
        return d

    def _get(self, url, **kwargs):
        if 'data' in kwargs and  not kwargs['data'] is None:
            url = '%s?%s' % (url, urlencode(kwargs['data']))
            del kwargs['data']
        return self._request(url, method=txhttp.get, **kwargs)

    def _post(self, url, **kwargs):
        return self._request(url, method=txhttp.post, **kwargs)

    def _delete(self, url, **kwargs):
        return self._request(url, method=txhttp.delete, **kwargs)

    #######################################
    # Public API
    #######################################

    def images(self, name=None):
        if name:
            q = {'all': 0, 'filter': name}
        else:
            q = None
        r = self._get('images/json', data=q)
        r.addCallback(json_response)
        return r

    @inlineCallbacks
    def build_image(self, dockerfile, ticket_id=None):
        headers = {'Content-Type': 'application/tar'}

        result = {}

        def on_content(chunk):
            self.task_log(ticket_id, chunk)

            if not 'image_id' in result:
                match = re.search(r'Successfully built ([0-9a-f]+)', chunk)
                if match:
                    result['image_id'] = match.group(1)

        response = yield self._post('build', data=dockerfile, headers=headers, response_handler=None)
        yield txhttp.collect(response, on_content)
        defer.returnValue(result['image_id'])

    @inlineCallbacks
    def put_file(self, container_id, path, file_data, ticket_id=None):

        config = {
            'AttachStdin': False,
            'Cmd': ['bash', '-c', 'echo %(data)s | base64 -d | tee %(path)s && chmod +x %(path)s' % {
                'data': base64.encodestring(file_data).strip(),
                'path': path
            }]
        }

        response = yield self._post('containers/%s/exec' % bytes(container_id),
                                    headers={'Content-Type': 'application/json'}, data=json.dumps(config), response_handler=None)

        data = yield self.collect_json_or_none(response)

        print(data)
        print(config)

        response = yield self._post('exec/%s/start' % bytes(data['Id']),
                                    headers={'Content-Type': 'application/json'}, data=json.dumps({
                 "Detach": False,
                 "Tty": False,
                }), response_handler=None)

        resp = yield txhttp.content(response)
        print(resp)


    def pull(self, name, ticket_id, tag=None):

        logger.debug('[%s] Pulling image "%s"', ticket_id, name)

        def on_content(chunk):
            logger.debug('[%s] Content chunk <%s>', ticket_id, chunk)
            self.task_log(ticket_id, chunk)

            try:
                data = json.loads(chunk)
                if 'error' in data:
                    raise CommandFailed('Failed to pull image "%s": %s' % (name, data['error']))

                return data

            except ValueError:
                pass

        def done(*args):
            logger.debug('[%s] Done pulling image.', ticket_id)
            return True

        create_params = {'fromImage': name}
        if tag:
            create_params['tag'] = tag

        r = self._post('images/create', params=create_params, response_handler=None)
        r.addCallback(txhttp.collect, on_content)
        r.addCallback(done)

        return r

    def collect_to_exception(self, e, response):
        def on_collected(content):
            raise e(content)
        d = txhttp.content(response)
        d.addCallback(on_collected)
        return d


    def logs(self, container_id, on_log, tail=0, follow=True):

        r = self._get('containers/%s/logs' % bytes(container_id),
            headers={'Connection': 'Upgrade', 'Upgrade': 'tcp'},
            response_handler=None, data={

            'follow': follow,
            'tail': tail,
            # 'timestamps': 0,
            'stdout': True,
            'stderr': True
        })
        def on_result(result):

            print(str(result.code) * 100)

            if result.code == 200:
                    return txhttp.collect(result, on_log)
            elif result.code == 404:
                return self.collect_to_exception(NotFound, result)
            else:
                return self.collect_to_exception(CommandFailed, result)

        r.addBoth(on_result)
        return r

    @inlineCallbacks
    def attach(self, container_id, ticket_id, skip_terminal=False):

        d = defer.Deferred()
        protocol = Attach(d, container_id)

        def stdin_on_input(channel, data):
            protocol.stdin_on_input(data)

        def stdout_write(data):
            self.task_stdout(ticket_id, data)

        def log_write(data):
            self.task_log(ticket_id, b64decode(data))

        try:
            if skip_terminal:
                protocol.stdout_write = log_write
            else:
                protocol.stdout_write = stdout_write

                self.eb.on('task.stdin.%s' % int(ticket_id), stdin_on_input)

            f = AttachFactory(protocol)

            proto, url = self.url.split('://')
            url = url.strip('/')

            print('url::::::::::::::::')
            print(url)
            if ':' in url:
                host, port = url.split(':')
            else:
                host = url
                port = 2376 if proto == 'https' else 2375

            if proto == 'https':
                from mcloud.ssl import CtxFactory
                pkey = load_privatekey(FILETYPE_PEM, self.key)
                cert = load_certificate(FILETYPE_PEM, self.crt)
                reactor.connectSSL(host, int(port), f, CtxFactory(pkey, cert))
            else:
                if proto == 'unix':
                    reactor.connectUNIX(host, f)
                else:
                    reactor.connectTCP(host, port, f)


            yield d

        finally:
            if not skip_terminal:
                self.eb.cancel('task.stdin.%s' % int(ticket_id), stdin_on_input)


    def events(self, on_event):
        r = self._get('events', response_handler=None)

        def event_parser(event):
            on_event(json.loads(event))

        r.addCallback(txhttp.collect, event_parser)
        return r

    @inlineCallbacks
    def create_container(self, config, name, ticket_id):

        logger.debug('[%s] Create container "%s"', ticket_id, name)

        result = yield self._post('containers/create', params={'name': name}, headers={'Content-Type': 'application/json'}, data=json.dumps(config))

        if result.code == 201:
            defer.returnValue(True)

        elif result.code == 409: # created
            defer.returnValue(True)

        else:
            content = yield result.content()
            raise CommandFailed('Create command returned unexpected status: %s. Result: %s' % (result.code, content))

    def collect_json_or_none(self, response):

        def on_collected(result):
            if response.code == 404:
                return None
            else:
                return json.loads(result)

        d = txhttp.content(response)
        d.addCallback(on_collected)

        return d

    @inlineCallbacks
    def stats(self, id):
        assert not id is None
        r = yield self._get('containers/%s/stats?stream=false' % bytes(id))
        r = yield self.collect_json_or_none(r)
        defer.returnValue(r)

    @inlineCallbacks
    def inspect(self, id):
        assert not id is None
        r = yield self._get('containers/%s/json' % bytes(id))
        r = yield self.collect_json_or_none(r)
        defer.returnValue(r)

    @inlineCallbacks
    def inspect_image(self, id):
        assert not id is None
        r = yield self._get('images/%s/json' % bytes(id))
        r = yield self.collect_json_or_none(r)
        defer.returnValue(r)

    @inlineCallbacks
    def resize(self, container_id, width, height):
        assert not id is None
        r = yield self._post(str("containers/%s/resize" % container_id), params={'h': height, 'w': width})
        logger.info({'h': height, 'w': width})
        r = yield txhttp.content(r)
        defer.returnValue(r)

    def list(self):
        r = self._get('containers/json')
        r.addCallback(self.collect_json_or_none)
        return r

    def version(self):
        r = self._get('version')
        r.addCallback(self.collect_json_or_none)
        return r

    @inlineCallbacks
    def remove_container(self, id, ticket_id):
        result = yield self._delete('containers/%s' % bytes(id))
        defer.returnValue(result.code == 204)

    @inlineCallbacks
    def start_container(self, id, ticket_id, config=None):

        logger.debug('[%s] Start container "%s"', ticket_id, id)

        if config is None:
            config = {}

        result = yield self._post('containers/%s/start' % bytes(id), headers={'Content-Type': 'application/json'}, data=json.dumps(config))
        defer.returnValue(result.code == 204)

    @inlineCallbacks
    def stop_container(self, id, ticket_id):
        result = yield self._post('containers/%s/stop' % bytes(id))
        defer.returnValue(result.code == 204)

    @inlineCallbacks
    def pause_container(self, id, ticket_id):
        result = yield self._post('containers/%s/pause' % bytes(id))
        defer.returnValue(result.code == 204)

    @inlineCallbacks
    def pause_container(self, id, ticket_id):
        result = yield self._post('containers/%s/unpause' % bytes(id))
        defer.returnValue(result.code == 204)

    @inlineCallbacks
    def find_container_by_name(self, name):
        result = yield self._get('containers/%s/json' % str(name))

        if result.code != 200:
            defer.returnValue(None)

        ct = yield txhttp.json_content(result)

        defer.returnValue(ct['Id'])

    @inlineCallbacks
    def find_containers_by_names(self, names):
        result = yield self._get('containers/json?all=1')
        response = yield txhttp.json_content(result)

        ids = dict([(name, None) for name in names])

        for ct in response:
            for name in names:
                if ('/%s' % name) in ct['Names']:
                    ids[name] = ct['Id']

        defer.returnValue(ids)
