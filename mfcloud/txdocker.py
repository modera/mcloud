import json
import logging
from urllib import urlencode
import inject
from mfcloud import txhttp
from mfcloud.util import Interface
import re
import treq
from twisted.internet import defer
from twisted.web._newclient import ResponseFailed
from txzmq import ZmqPubConnection

logger = logging.getLogger('mfcloud.docker')

class IDockerClient(Interface):
    pass


def json_response(result):
        return txhttp.json_content(result)

class CommandFailed(Exception):
    pass


class DockerTwistedClient(object):

    message_publisher = inject.attr(ZmqPubConnection)

    def __init__(self, url='unix://var/run/docker.sock//'):
        super(DockerTwistedClient, self).__init__()

        self.url = url

    def _request(self, url, method=txhttp.get, **kwargs):
        d = method('%s%s' % (self.url, url), **kwargs)

        def error(failure):
            e = Exception('Can not connect to docker: %s' % failure.getErrorMessage())
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

    def build_image(self, dockerfile, ticket_id=None):

        headers = {'Content-Type': 'application/tar'}

        result = {}

        def on_content(chunk):
            print chunk

            if ticket_id and self.message_publisher:
                self.message_publisher.publish(chunk, 'log-%s' % ticket_id)

            if not 'image_id' in result:
                match = re.search(r'Successfully built ([0-9a-f]+)', chunk)
                if match:
                    result['image_id'] = match.group(1)

        def done(*args):
            return result['image_id']

        def err(failure):
            failure.trap(ResponseFailed)
            raise failure.value.reasons[0]

        r = self._post('build', data=dockerfile, headers=headers, response_handler=None)

        def before_collect(response):
            # print response.code
            # print response.headers
            # print response.length

            return txhttp.collect(response, on_content)

        r.addCallback(before_collect)
        r.addCallback(done)
        r.addErrback(err)

        print 'jpjpjp'
        return r


    def pull(self, name, ticket_id):

        logger.debug('[%s] Pulling image "%s"', ticket_id, name)

        def on_content(chunk):

            logger.debug('[%s] Content chunk <%s>', ticket_id, chunk)

            if ticket_id and self.message_publisher:
                self.message_publisher.publish(chunk, 'log-%s' % ticket_id)

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

    def create_container(self, config, name, ticket_id):

        d = self._post('containers/create', params={'name': name}, headers={'Content-Type': 'application/json'}, data=json.dumps(config))

        def done(result):
            if result.code != 201:
                return None
            return txhttp.json_content(result)

        d.addCallback(done)
        return d

    def collect_json_or_none(self, response):

        def on_collected(result):
            if response.code == 404:
                return None
            else:
                return json.loads(result)

        d = txhttp.content(response)
        d.addCallback(on_collected)

        return d

    def inspect(self, id):
        r = self._get('containers/%s/json' % bytes(id))
        r.addCallback(self.collect_json_or_none)
        return r

    def remove_container(self, id, ticket_id):
        r = self._delete('containers/%s' % bytes(id))

        def done(result):
            return result.code == 204

        r.addCallback(done)
        #
        # def error(r):
        #     return False
        #
        # r.addErrback(error)

        return r

    def start_container(self, id, ticket_id):
        r = self._post('containers/%s/start' % bytes(id))

        def done(result):
            return result.code == 204

        r.addCallback(done)
        #
        # def error(r):
        #     return False
        #
        # r.addErrback(error)

        return r

    def stop_container(self, id, ticket_id):
        r = self._post('containers/%s/stop' % bytes(id))

        def done(result):
            return result.code == 204

        r.addCallback(done)

        # def error(r):
        #     return False
        #
        # r.addErrback(error)

        return r

    def find_container_by_name(self, name):
        r = self._get('containers/json?all=1')

        def on_response(response):
            for ct in response:
                if ('/%s' % name) in ct['Names']:
                    return ct['Id']
            return None

        r.addCallback(txhttp.json_content)
        r.addCallback(on_response)

        # def error(r):
        #     return None
        #
        # r.addErrback(error)

        return r
