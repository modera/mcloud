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

    def _request(self, url, method=txhttp.get, response_handler=json_response, **kwargs):

        d = method('%s%s' % (self.url, url), **kwargs)

        if response_handler:
            d.addCallback(response_handler)

        return d

    def _get(self, url, **kwargs):
        if 'data' in kwargs and  not kwargs['data'] is None:
            url = '%s?%s' % (url, urlencode(kwargs['data']))
            del kwargs['data']
        return self._request(url, method=txhttp.get, **kwargs)

    def _post(self, url, **kwargs):
        return self._request(url, method=txhttp.post, **kwargs)

    #######################################
    # Public API
    #######################################

    def images(self, name=None):
        if name:
            q = {'all': 0, 'filter': name}
        else:
            q = None
        return self._get('images/json', data=q)

    def build_image(self, dockerfile):

        headers = {'Content-Type': 'application/tar'}

        result = {}
        def on_content(chunk):

            #print 'Data chunk: %s' % chunk

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