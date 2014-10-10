

import re
from twisted.internet.endpoints import UNIXClientEndpoint
from twisted.web.client import Agent, _URI

from treq.client import HTTPClient
from treq._utils import default_pool, default_reactor

from treq.content import collect, content, text_content, json_content


class UNIXAwareHttpClient(HTTPClient):
    def request(self, method, url, **kwargs):
        return super(UNIXAwareHttpClient, self).request(method, url, **kwargs)


class UNIXAwareHttpAgent(Agent):

    def request(self, method, uri, headers=None, bodyProducer=None):
        """
        Issue a request to the server indicated by the given C{uri}.

        An existing connection from the connection pool may be used or a new one may be created.

        I{HTTP} and I{HTTPS} schemes are supported in C{uri}.

        @see: L{twisted.web.iweb.IAgent.request}
        """

        if uri.startswith('unix://'):
            unix_uri = re.match('^unix://(.*)//(.*)', uri)

            if not unix_uri:
                raise ValueError('Unix pipe http uri format is incorrect.')

            filename = '/%s' % unix_uri.group(1)
            endpoint = UNIXClientEndpoint(self._reactor, filename)

            parsedURI = _URI.fromBytes('unix://unix/%s' % unix_uri.group(2))
            parsedURI.host = unix_uri.group(1)

            key = (parsedURI.scheme, parsedURI.host, parsedURI.port)

            return self._requestWithEndpoint(key, endpoint, method, parsedURI,
                                         headers, bodyProducer,
                                         parsedURI.originForm)

        return super(UNIXAwareHttpAgent, self).request(method, uri, headers, bodyProducer)



def head(url, **kwargs):
    """
    Make a ``HEAD`` request.

    See :py:func:`treq.request`
    """
    return _client(**kwargs).head(url, **kwargs)


def get(url, headers=None, **kwargs):
    """
    Make a ``GET`` request.

    See :py:func:`treq.request`
    """
    return _client(**kwargs).get(url, headers=headers, **kwargs)


def post(url, data=None, **kwargs):
    """
    Make a ``POST`` request.

    See :py:func:`treq.request`
    """
    return _client(**kwargs).post(url, data=data, **kwargs)


def put(url, data=None, **kwargs):
    """
    Make a ``PUT`` request.

    See :py:func:`treq.request`
    """
    return _client(**kwargs).put(url, data=data, **kwargs)


def patch(url, data=None, **kwargs):
    """
    Make a ``PATCH`` request.

    See :py:func:`treq.request`
    """
    return _client(**kwargs).patch(url, data=data, **kwargs)


def delete(url, **kwargs):
    """
    Make a ``DELETE`` request.

    See :py:func:`treq.request`
    """
    return _client(**kwargs).delete(url, **kwargs)


def request(method, url, **kwargs):
    """
    Make an HTTP request.

    :param str method: HTTP method. Example: ``'GET'``, ``'HEAD'``. ``'PUT'``,
         ``'POST'``.
    :param str url: http or https URL, which may include query arguments.

    :param headers: Optional HTTP Headers to send with this request.
    :type headers: Headers or None

    :param params: Optional parameters to be append as the query string to
        the URL, any query string parameters in the URL already will be
        preserved.

    :type params: dict w/ str or list/tuple of str values, list of 2-tuples, or
        None.

    :param data: Optional request body.
    :type data: str, file-like, IBodyProducer, or None

    :param reactor: Optional twisted reactor.

    :param bool persistent: Use persistent HTTP connections.  Default: ``True``
    :param bool allow_redirects: Follow HTTP redirects.  Default: ``True``

    :param auth: HTTP Basic Authentication information.
    :type auth: tuple of ('username', 'password').

    :param int timeout: Request timeout seconds. If a response is not
        received within this timeframe, a connection is aborted with
        ``CancelledError``.

    :rtype: Deferred that fires with an IResponse provider.

    """
    return _client(**kwargs).request(method, url, **kwargs)


def _client(*args, **kwargs):
    reactor = default_reactor(kwargs.get('reactor'))
    pool = default_pool(reactor,
                        kwargs.get('pool'),
                        persistent=False)
                        #kwargs.get('persistent'))
    agent = UNIXAwareHttpAgent(reactor, pool=pool)
    return UNIXAwareHttpClient(agent)