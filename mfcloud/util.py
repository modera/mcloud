from contextlib import contextmanager
from abc import ABCMeta
import inject

def format_service_status(service):
    if len(service.containers()):
        s = []
        for ct in service.containers(stopped=True):
            if ct.is_running:
                s.append('UP[%s]' % ct.human_readable_ports)
            else:
                s.append('DOWN')

        service_status = ','.join(s)

    else:
        service_status = 'NO CONTAINERS'
    return service_status


class Interface(object):
    __metaclass__ = ABCMeta


def accepts(*types):
    def check_accepts(f):

        #assert len(types) == f.func_code.co_argcount

        def new_f(*args, **kwds):

            check_args = args
            if f.func_code.co_argcount > 0 and f.func_code.co_varnames[0] == 'self':
                check_args = check_args[1:]

            for (a, t) in zip(check_args, types):
                if not isinstance(a, t):
                    raise TypeError("arg %r does not match %s" % (a, t))

            return f(*args, **kwds)

        new_f.func_name = f.func_name
        return new_f
    return check_accepts


def abstract(class_to_mock):

    abstract_methods = {}

    for name, item in class_to_mock.__dict__.items():
        if hasattr(item, '__isabstractmethod__') and item.__isabstractmethod__ is True:
            abstract_methods[name] = lambda: None

    return type('%s_mock_' % class_to_mock.__name__, (class_to_mock,), abstract_methods)()

@contextmanager
def inject_services(configurator):
    inject.clear_and_configure(configurator)
    yield
    inject.clear()
