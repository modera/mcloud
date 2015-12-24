from configurations import importer
import os
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks


@inlineCallbacks
def test():

    os.environ['DJANGO_SETTINGS_MODULE'] = 'mcloud.app.settings'
    os.environ['DJANGO_CONFIGURATION'] = 'Dev'
    importer.install()


    from mcloud.app.models import Deployment
    deployements = yield Deployment.tx.all()

    print(deployements)


reactor.callLater(0, test)

reactor.run()