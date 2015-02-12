from mcloud.ssl import listen_ssl
import os
from klein import Klein
from twisted.internet import reactor
from twisted.internet.defer import succeed, inlineCallbacks
from twisted.web.server import Site
from twisted.web.static import File
from pkg_resources import resource_filename

static_dir = resource_filename(__name__, 'static/')

app = Klein()
@app.route('/', branch=True)
def static(request):
    return File(static_dir)

app_redirect = Klein()
@app_redirect.route('/', branch=True)
def static(request):
    request.redirect('https://%s' % request.getHost())
    return succeed(None)


def listen_web(settings):
    """
    @type settings: mcloud.rpc_server.McloudConfiguration
    """

    if settings and settings.ssl.enabled:

        print '*' * 40
        print 'Listen web on port *:7085 (SSL)'
        print '*' * 40

        listen_ssl(Site(app.resource()), settings.web_ip, 443)
        reactor.listenTCP(80, Site(app_redirect.resource()), interface=settings.web_ip)
    else:
        print '*' * 40
        print 'Listen web on port *:7085 (Insecure)'
        print '*' * 40

        reactor.listenTCP(80, Site(app.resource()), interface=settings.web_ip)
