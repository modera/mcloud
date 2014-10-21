from base64 import b64encode, b64decode
import pty
from twisted.internet import defer
from twisted.internet.protocol import Factory, ClientFactory
from twisted.protocols import basic
from twisted.python import log
from twisted.web.http import PotentialDataLoss
from twisted.internet import reactor, defer
# dockerpty: tty.py
#
# Copyright 2014 Chris Corbyn <chris@w3style.co.uk>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

import os
import termios
import tty
import fcntl
import struct
from twisted.internet.protocol import Protocol



class Terminal(object):
    """
    Terminal provides wrapper functionality to temporarily make the tty raw.

    This is useful when streaming data from a pseudo-terminal into the tty.

    Example:

        with Terminal(sys.stdin, raw=True):
            do_things_in_raw_mode()
    """

    def __init__(self, fd, raw=True):
        """
        Initialize a terminal for the tty with stdin attached to `fd`.

        Initializing the Terminal has no immediate side effects. The `start()`
        method must be invoked, or `with raw_terminal:` used before the
        terminal is affected.
        """

        self.fd = fd
        self.raw = raw
        self.original_attributes = None


    def __enter__(self):
        """
        Invoked when a `with` block is first entered.
        """

        self.start()
        return self


    def __exit__(self, *_):
        """
        Invoked when a `with` block is finished.
        """

        self.stop()

    def get_size(self):
        if not os.isatty(self.fd.fileno()):
            return None

        try:
            dims = struct.unpack('hh', fcntl.ioctl(self.fd, termios.TIOCGWINSZ, 'hhhh'))
        except:
            try:
                dims = (os.environ['LINES'], os.environ['COLUMNS'])
            except:
                return None
        return dims

    def israw(self):
        """
        Returns True if the TTY should operate in raw mode.
        """

        return self.raw

    def start(self):
        """
        Saves the current terminal attributes and makes the tty raw.

        This method returns None immediately.
        """

        if os.isatty(self.fd.fileno()) and self.israw():
            self.original_attributes = termios.tcgetattr(self.fd)
            tty.setraw(self.fd)


    def stop(self):
        """
        Restores the terminal attributes back to before setting raw mode.

        If the raw terminal was not started, does nothing.
        """

        if self.original_attributes is not None:
            termios.tcsetattr(
                self.fd,
                termios.TCSADRAIN,
                self.original_attributes,
            )

    def __repr__(self):
        return "{cls}({fd}, raw={raw})".format(
            cls=type(self).__name__,
            fd=self.fd,
            raw=self.raw)


from twisted.internet import stdio, reactor
from twisted.protocols import basic
from twisted.web import client

class AttachStdinProtocol(Protocol):

    def __init__(self):
        self.listener = None
        self.term = Terminal(sys.stdin, raw=True)
        self.started = False

    def write(self, data):
        if not self.started:
            self.term.start()
            self.started = True

        self.transport.write(b64decode(data))

    def stop(self):
        self.transport.loseConnection()

    def connectionLost(self, reason):
        Protocol.connectionLost(self, reason)
        self.term.stop()

    def dataReceived(self, data):
        if len(data) == 1 and ord(data) == 29:
            self.transport.loseConnection()
            reactor.stop()

        if self.listener:
            self.listener(b64encode(data))


class Attach(basic.LineReceiver):

    def __init__(self, finnished, container_id):
        self.finished = finnished
        self.container_id = container_id

    def connectionMade(self):
        """ """
        self.transport.write('POST /containers/%s/attach?logs=1&stream=1&stdout=1&stdin=1 HTTP/1.1\r\n' % str(self.container_id))
        self.transport.write('\r\n')

    def rawDataReceived(self, data):
        self.stdout_write(b64encode(data))

    def lineReceived(self, line):
        if line.strip() == '':
            self.setRawMode()

    def stdin_on_input(self, data):
        self.transport.write(b64decode(data))

    def stdout_write(self, data):
        pass

    def connectionLost(self, reason):

        # from twisted.internet.error import ConnectionDone
        # basic.LineReceiver.connectionLost(self, reason)

        if reason.check(PotentialDataLoss):
            # http://twistedmatrix.com/trac/ticket/4840
            self.finished.callback(None)
        else:
            self.finished.errback(reason)


class AttachFactory(ClientFactory):
    """ file sender factory """
    def __init__(self, protocol):
        """ """
        self.protocol = protocol

    def buildProtocol(self, addr):
        """ """
        p = self.protocol
        p.factory = self
        return p


def attach_to_container(container_id, docker_uri=None):

    with Terminal(sys.stdin, raw=True):

        d = defer.Deferred()

        stream_proto = AttachStdinProtocol()

        protocol = Attach(d, container_id, stream_proto)
        f = AttachFactory(protocol)
        reactor.connectUNIX('/var/run/docker.sock', f)

        stdio.StandardIO(stream_proto)

        reactor.run()

if __name__ == "__main__":
    attach_to_container('606d')

