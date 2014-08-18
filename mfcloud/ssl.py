import inject

from twisted.internet import ssl


class CtxFactory(ssl.ClientContextFactory):

    settings = inject.attr('settings')

    def getContext(self):
        from OpenSSL import SSL

        self.method = SSL.SSLv23_METHOD
        ctx = ssl.ClientContextFactory.getContext(self)
        ctx.use_certificate_file(self.settings.ssl.cert)
        ctx.use_privatekey_file(self.settings.ssl.key)

        return ctx
