
class Plugin(object):
    pass


class PluginFatalError(Exception):
    pass


class PluginInitError(PluginFatalError):
    pass