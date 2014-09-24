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

from __future__ import absolute_import

import os
import termios
import tty
import fcntl
import struct


def size(fd):
    """
    Return a tuple (rows,cols) representing the size of the TTY `fd`.

    The provided file descriptor should be the stdout stream of the TTY.

    If the TTY size cannot be determined, returns None.
    """

    if not os.isatty(fd.fileno()):
        return None

    try:
        dims = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, 'hhhh'))
    except:
        try:
            dims = (os.environ['LINES'], os.environ['COLUMNS'])
        except:
            return None

    return dims


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


import array
import fcntl
import os
import pty
import termios
import tty

import zmq
from zmq.eventloop import ioloop
from zmq.eventloop.zmqstream import ZMQStream
import sys
from zmq.eventloop import ioloop
ioloop.install()


def connect_sockets():
   context = zmq.Context()

   socket_out = context.socket(zmq.PUB)

   socket_out.curve_publickey = b"Yne@$w-vo<fVvi]a<NY6T1ed:M$fCG*[IaLV{hID"
   socket_out.curve_secretkey = b"D:)Q[IlAW!ahhC2ac:9*A}h:p?([4%wOTJ%JR%cs"
   socket_out.curve_serverkey = b"rq:rM>}U?@Lns47E1%kR.o@n%FcmmsL/@{H8]yf7"

   socket_out.connect("tcp://127.0.0.1:5556")


   # -------------------------------------

   context_in = zmq.Context()
   socket_in = context_in.socket(zmq.SUB)

   socket_in.curve_publickey = b"Yne@$w-vo<fVvi]a<NY6T1ed:M$fCG*[IaLV{hID"
   socket_in.curve_secretkey = b"D:)Q[IlAW!ahhC2ac:9*A}h:p?([4%wOTJ%JR%cs"
   socket_in.curve_serverkey = b"rq:rM>}U?@Lns47E1%kR.o@n%FcmmsL/@{H8]yf7"

   socket_in.setsockopt(zmq.SUBSCRIBE, "")
   socket_in.connect("tcp://127.0.0.1:5557")

   in_stream = ZMQStream(socket_in)

   return socket_out, in_stream


def exec_with_remote_screen(args, in_stream, out_stream):

   restore = 0
   mode = None
   pid, master_fd = pty.fork()

   if pid == pty.CHILD:

       os.execlp(args[0], *args)

       ioloop.IOLoop.instance().stop()

       os.close(master_fd)

       if restore:
           tty.tcsetattr(pty.STDIN_FILENO, tty.TCSAFLUSH, mode)

   else:

       def on_message(msg):
           msg = msg[0]
           cmd = msg[0:3]
           msg = msg[4:]

           if cmd == 'inp':
               os.write(master_fd, msg)


       def on_data(fd, events):
           try:
               data = os.read(fd, 1024)
               out_stream.send('scr %s' % data)
               os.write(pty.STDOUT_FILENO, data)
           except OSError:
               ioloop.IOLoop.instance().stop()


       def on_term_input(fd, events):
           data = os.read(fd, 1024)
           os.write(master_fd, data)
           #log.write(data)
           #log.flush()

       buf = array.array('h', [0, 0, 0, 0])
       fcntl.ioctl(pty.STDOUT_FILENO, termios.TIOCGWINSZ, buf, True)
       fcntl.ioctl(master_fd, termios.TIOCSWINSZ, buf)


       mode = tty.tcgetattr(pty.STDIN_FILENO)
       try:
           try:
               tty.setraw(pty.STDIN_FILENO)
               restore = 1
           except tty.error:    # This is the same as termios.error
               restore = 0

           in_stream.on_recv(on_message)

           ioloop.IOLoop.instance().add_handler(master_fd, on_data, ioloop.IOLoop.READ)
           ioloop.IOLoop.instance().add_handler(pty.STDIN_FILENO, on_term_input, ioloop.IOLoop.READ)
           ioloop.IOLoop.instance().start()

       finally:
           os.close(master_fd)

           if restore:
               tty.tcsetattr(pty.STDIN_FILENO, tty.TCSAFLUSH, mode)

           #log.close()
