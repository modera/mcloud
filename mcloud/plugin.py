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

    print 'Resolving interface ', interface

    try:
        plugins = inject.instance('plugins')
    except inject.InjectorException:
        print 'Resolver can not get access to plugins'
        return

    for plugin in plugins:
        try:
            adaptor = interface(plugin)

            print plugin, adaptor
            if adaptor:
                verifyObject(interface, adaptor)
                yield adaptor
        except TypeError as e:
            print e