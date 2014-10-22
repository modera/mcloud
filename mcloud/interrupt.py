import signal

from twisted.internet.defer import inlineCallbacks


class InterruptCancel(Exception):
    pass

class InterruptManager(object):

    interrupt_stack = []

    def append(self, handler):
        self.interrupt_stack.append(handler)

    @inlineCallbacks
    def handle_interrupt(self, manual=False, *args):
        try:
            last = None
            for itr in reversed(self.interrupt_stack):
                yield itr.interrupt(last)

                self.interrupt_stack.remove(itr)

                last = itr

        except InterruptCancel:
            pass

    def manual_interrupt(self):
        return self.handle_interrupt(manual=True)

    def register_interupt_handler(self):
        signal.signal(signal.SIGINT, self.handle_interrupt)
