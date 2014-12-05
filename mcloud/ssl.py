import datetime
import inject

from twisted.internet import ssl, reactor
from twisted.internet.defer import inlineCallbacks
import txredisapi


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


def verifyCallback(connection, x509, errnum, errdepth, ok):

    if not ok:
        print 'invalid cert from subject:', x509.get_subject()
        return False
    else:
        print 'Subject is: %s' % x509.get_subject().commonName
        print "Certs are fine"

        # return False
    return True

def listen_ssl(port, resource, interface):

    settings = inject.instance('settings')

    from OpenSSL import SSL

    from twisted.internet import ssl

    myContextFactory = ssl.DefaultOpenSSLContextFactory(
        settings.ssl.key, settings.ssl.cert, sslmethod=SSL.SSLv23_METHOD
    )
    ctx = myContextFactory.getContext()

    ctx.set_verify(SSL.VERIFY_PEER | SSL.VERIFY_CLIENT_ONCE | SSL.VERIFY_FAIL_IF_NO_PEER_CERT, verifyCallback)
    ctx.set_session_cache_mode(SSL.SESS_CACHE_BOTH)

    # Since we have self-signed certs we have to explicitly
    # tell the server to trust them.

    ctx.load_verify_locations(settings.ssl.ca)
    ctx.set_session_id(str(datetime.datetime.now()))

    reactor.listenSSL(port, resource, myContextFactory, interface=interface)
