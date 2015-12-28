from OpenSSL.crypto import FILETYPE_PEM
import re
from twisted.internet import ssl
from twisted.internet._sslverify import optionsForClientTLS, PrivateCertificate, KeyPair, Certificate, _tolerateErrors
from twisted.internet.endpoints import UNIXClientEndpoint
from twisted.web.client import Agent, URI, BrowserLikePolicyForHTTPS, _requireSSL

from treq.client import HTTPClient
from treq._utils import default_pool, default_reactor

from treq.content import collect, content, text_content, json_content
from twisted.web.error import PageRedirect
from twisted.web.iweb import IPolicyForHTTPS
from zope.interface import implementer


class UNIXAwareHttpClient(HTTPClient):
    def request(self, method, url, **kwargs):
        print(method)
        print(url)
        return super(UNIXAwareHttpClient, self).request(method, url, **kwargs)


class CtxFactory(ssl.ClientContextFactory):

    def __init__(self, key, crt):
        self.key = key
        self.crt = crt

    def getContext(self):
        from OpenSSL import SSL

        self.method = SSL.SSLv23_METHOD
        ctx = ssl.ClientContextFactory.getContext(self)
        ctx.use_certificate_file(self.crt)
        ctx.use_privatekey_file(self.key)

        return ctx


@implementer(IPolicyForHTTPS)
class BrowserLikeTLSPolicyForHTTPS(object):
    """
    SSL connection creator for web clients.
    """
    def __init__(self, key, crt, ca):
        self._trustRoot = None
        self.key = key
        self.crt = crt
        self.ca = ca

    def _identityVerifyingInfoCallback(self, connection, where, ret):
        pass

    @_requireSSL
    def creatorForNetloc(self, hostname, port):
        """
        Create a L{client connection creator
        <twisted.internet.interfaces.IOpenSSLClientConnectionCreator>} for a
        given network location.

        @param tls: The TLS protocol to create a connection for.
        @type tls: L{twisted.protocols.tls.TLSMemoryBIOProtocol}

        @param hostname: The hostname part of the URI.
        @type hostname: L{bytes}

        @param port: The port part of the URI.
        @type port: L{int}

        @return: a connection creator with appropriate verification
            restrictions set
        @rtype: L{client connection creator
            <twisted.internet.interfaces.IOpenSSLClientConnectionCreator>}
        """

        key_pair = KeyPair.load(self.key, format=FILETYPE_PEM)
        cert = PrivateCertificate.fromCertificateAndKeyPair(Certificate.loadPEM(self.crt), key_pair)

        authority = ssl.Certificate.loadPEM(self.ca)

        options = optionsForClientTLS(hostname.decode("ascii"), authority, clientCertificate=cert)

        # bypass hostname verification
        # options._identityVerifyingInfoCallback = self._identityVerifyingInfoCallback
        options._ctx.set_info_callback(
            _tolerateErrors(self._identityVerifyingInfoCallback)
        )
        return options

class UNIXAwareHttpAgent(Agent):

    def __init__(self, reactor, connectTimeout=None, bindAddress=None,
                 pool=None, key=None, crt=None, ca=None, **kwargs):

        contextFactory = BrowserLikeTLSPolicyForHTTPS(key, crt, ca)
        super(UNIXAwareHttpAgent, self).__init__(reactor, contextFactory, connectTimeout, bindAddress, pool)
    #
    # def _getEndpoint(self, scheme, host, port):
    #     endpoint = super(UNIXAwareHttpAgent, self)._getEndpoint(scheme, host, port)
    #
    #     if isinstance()
    #
    #     return endpoint

    def request(self, method, uri, headers=None, bodyProducer=None, follow_redirects=2):
        """
        Issue a request to the server indicated by the given C{uri}.

        An existing connection from the connection pool may be used or a new one may be created.

        I{HTTP} and I{HTTPS} schemes are supported in C{uri}.

        @see: L{twisted.web.iweb.IAgent.request}
        """
        if uri.startswith(b'unix://'):
            unix_uri = re.match(b'^unix://(.*)//(.*)', uri)

            if not unix_uri:
                raise ValueError('Unix pipe http uri format is incorrect.')

            filename = '/%s' % unix_uri.group(1)
            endpoint = UNIXClientEndpoint(self._reactor, filename)

            parsedURI = URI.fromBytes(b'unix://unix/%s' % unix_uri.group(2))
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
    return _client(key=None, crt=None,**kwargs).put(url, data=data, **kwargs)


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
    agent = UNIXAwareHttpAgent(reactor, pool=pool, **kwargs)
    return UNIXAwareHttpClient(agent)