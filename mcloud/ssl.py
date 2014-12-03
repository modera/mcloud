import inject

from twisted.internet import ssl


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
