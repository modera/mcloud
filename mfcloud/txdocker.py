import json
from urllib import urlencode
from mfcloud import txhttp
from mfcloud.util import Interface
import re
import treq


class IDockerClient(Interface):
    pass


def json_response(result):
        return txhttp.json_content(result)


class DockerTwistedClient(object):

    def __init__(self, url='unix://var/run/docker.sock//'):
        super(DockerTwistedClient, self).__init__()

        self.url = url
        self.message_publisher = None

    def _request(self, url, method=txhttp.get, **kwargs):
        return method('%s%s' % (self.url, url), **kwargs)

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

            #print 'Data chunk: %s' % chunk
            if ticket_id and self.message_publisher:
                self.message_publisher(ticket_id, 'log', json.loads(chunk)['stream'])

            if not 'image_id' in result:
                match = re.search(r'Successfully built ([0-9a-f]+)', chunk)
                if match:
                    result['image_id'] = match.group(1)

        def done(*args):
            return result['image_id']

        r = self._post('build', data=dockerfile, headers=headers, response_handler=None)
        r.addCallback(txhttp.collect, on_content)
        r.addCallback(done)

        return r


    def pull(self, name=None):
        pass

    def create_container(self, config, name, ticket_id):

        d = self._post('containers/create', params={'name': name}, headers={'Content-Type': 'application/json'}, data=json.dumps(config))

        def done(result):
            if result.code != 201:
                return None
            return txhttp.json_content(result)

        d.addCallback(done)
        return d

    def inspect(self, id):
        r = self._get('containers/%s/json' % bytes(id))
        r.addCallback(txhttp.json_content)

        def error(r):
            return None

        r.addErrback(error)

        return r

    def remove_container(self, id, ticket_id):
        r = self._delete('containers/%s' % bytes(id))

        def done(result):
            return result.code == 204

        r.addCallback(done)

        def error(r):
            return False

        r.addErrback(error)

        return r

    def start_container(self, id, ticket_id):
        r = self._post('containers/%s/start' % bytes(id))

        def done(result):
            return result.code == 204

        r.addCallback(done)

        def error(r):
            return False

        r.addErrback(error)

        return r

    def stop_container(self, id, ticket_id):
        r = self._post('containers/%s/stop' % bytes(id))

        def done(result):
            return result.code == 204

        r.addCallback(done)

        def error(r):
            return False

        r.addErrback(error)

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

        def error(r):
            return None

        r.addErrback(error)

        return r
