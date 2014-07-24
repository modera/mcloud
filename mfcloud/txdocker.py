import json
import logging
from urllib import urlencode
from mfcloud import txhttp

from mfcloud.events import EventBus
from mfcloud.remote import ApiRpcServer
import os
import inject
from mfcloud.util import Interface
import re
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks

logger = logging.getLogger('mfcloud.docker')

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

    rpc_server = inject.attr(ApiRpcServer)
    eb = inject.attr(EventBus)

    def task_log(self, ticket_id, message):
        self.rpc_server.task_progress(message, ticket_id)

    def __init__(self, url=None):
        super(DockerTwistedClient, self).__init__()

        if url is None:
            url = os.environ.get('DOCKER_API_URL', 'unix://var/run/docker.sock/')

        self.url = url + '/'

    def _request(self, url, method=txhttp.get, **kwargs):

        url_ = '%s%s' % (self.url, url)
        d = method(url_, timeout=30, **kwargs)

        def error(failure):
            e = DockerConnectionFailed('Connection timeout: %s When connecting to: %s' % (failure.getErrorMessage(), url_))
            logger.error(e)
            raise e

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



    def pull(self, name, ticket_id):

        logger.debug('[%s] Pulling image "%s"', ticket_id, name)

        def on_content(chunk):
            logger.debug('[%s] Content chunk <%s>', ticket_id, chunk)
            self.task_log(ticket_id, chunk)

            try:
                data = json.loads(chunk)
                if 'error' in data:
                    raise CommandFailed('Failed to pull image "%s": %s' % (name, data['error']))

            except ValueError:
                pass

        def done(*args):
            logger.debug('[%s] Done pulling image.', ticket_id)
            return True

        r = self._post('images/create', params={'fromImage': name}, response_handler=None)
        r.addCallback(txhttp.collect, on_content)
        r.addCallback(done)

        return r

    def collect_to_exception(self, e, response):
        def on_collected(content):
            raise e(content)
        d = txhttp.content(response)
        d.addCallback(on_collected)
        return d


    def logs(self, container_id, on_log):
        r = self._get('containers/%s/logs' % bytes(container_id), response_handler=None, data={
            'follow': True,
            'stdout': True,
            'stderr': True
        })

        def on_result(result):
            if result.code == 200:
                return txhttp.collect(result, on_log)
            elif result.code == 404:
                return self.collect_to_exception(NotFound, result)
            else:
                return self.collect_to_exception(CommandFailed, result)

        r.addBoth(on_result)
        return r

    def events(self, on_event):
        r = self._get('events', response_handler=None)
        r.addCallback(txhttp.collect, on_event)
        return r

    @inlineCallbacks
    def create_container(self, config, name, ticket_id):

        logger.debug('[%s] Create container "%s"', ticket_id, name)

        result = yield self._post('containers/create', params={'name': name}, headers={'Content-Type': 'application/json'}, data=json.dumps(config))

        if result.code == 201:
            defer.returnValue(True)

        if result.code == 409: # created
            defer.returnValue(True)

        raise CommandFailed('Create command returned unexpected status: %s' % result.code)

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
    def inspect(self, id):
        assert not id is None
        r = yield self._get('containers/%s/json' % bytes(id))
        print r
        r = yield self.collect_json_or_none(r)
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
    def find_container_by_name(self, name):
        result = yield self._get('containers/%s/json' % str(name))

        if result.code != 200:
            defer.returnValue(None)

        ct = yield txhttp.json_content(result)

        defer.returnValue(ct['Id'])
