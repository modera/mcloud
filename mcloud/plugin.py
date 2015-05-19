import inject
from zope.interface import Interface
from zope.interface.verify import verifyObject


class IMcloudPlugin(Interface):
    """
    Describes basic behavior of plugin.
    """
    def setup():
        """
        Method called on plugin initialization.
        """


def enumerate_plugins(interface):
    try:
        plugins = inject.instance('plugins')
    except inject.InjectorException:
        return

    for plugin in plugins:
        try:
            adaptor = interface(plugin)
            if adaptor:
                verifyObject(interface, adaptor)
                yield adaptor
        except TypeError:
            pass