import inject
from mcloud.events import EventBus
from mcloud.plugin import IMcloudPlugin
from mcloud.plugins import Plugin
from twisted.internet.defer import inlineCallbacks
from zope.interface import implements

class {{cookiecutter.name|capitalize}}Plugin(Plugin):
    implements(IMcloudPlugin)

    eb = inject.attr(EventBus)
    settings = inject.attr('settings')

    @inlineCallbacks
    def setup(self):
        yield None
