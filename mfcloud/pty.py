#
#import array
#import fcntl
#import os
#import pty
#import termios
#import tty
#
#import zmq
#from zmq.eventloop import ioloop
#from zmq.eventloop.zmqstream import ZMQStream
#import sys
#from zmq.eventloop import ioloop
#ioloop.install()
#
#
#def connect_sockets():
#    context = zmq.Context()
#
#    socket_out = context.socket(zmq.PUB)
#
#    socket_out.curve_publickey = b"Yne@$w-vo<fVvi]a<NY6T1ed:M$fCG*[IaLV{hID"
#    socket_out.curve_secretkey = b"D:)Q[IlAW!ahhC2ac:9*A}h:p?([4%wOTJ%JR%cs"
#    socket_out.curve_serverkey = b"rq:rM>}U?@Lns47E1%kR.o@n%FcmmsL/@{H8]yf7"
#
#    socket_out.connect("tcp://127.0.0.1:5556")
#
#
#    # -------------------------------------
#
#    context_in = zmq.Context()
#    socket_in = context_in.socket(zmq.SUB)
#
#    socket_in.curve_publickey = b"Yne@$w-vo<fVvi]a<NY6T1ed:M$fCG*[IaLV{hID"
#    socket_in.curve_secretkey = b"D:)Q[IlAW!ahhC2ac:9*A}h:p?([4%wOTJ%JR%cs"
#    socket_in.curve_serverkey = b"rq:rM>}U?@Lns47E1%kR.o@n%FcmmsL/@{H8]yf7"
#
#    socket_in.setsockopt(zmq.SUBSCRIBE, "")
#    socket_in.connect("tcp://127.0.0.1:5557")
#
#    in_stream = ZMQStream(socket_in)
#
#    return socket_out, in_stream
#
#
#def exec_with_remote_screen(args, in_stream, out_stream):
#
#    restore = 0
#    mode = None
#    pid, master_fd = pty.fork()
#
#    if pid == pty.CHILD:
#
#        os.execlp(args[0], *args)
#
#        ioloop.IOLoop.instance().stop()
#
#        os.close(master_fd)
#
#        if restore:
#            tty.tcsetattr(pty.STDIN_FILENO, tty.TCSAFLUSH, mode)
#
#    else:
#
#        def on_message(msg):
#            msg = msg[0]
#            cmd = msg[0:3]
#            msg = msg[4:]
#
#            if cmd == 'inp':
#                os.write(master_fd, msg)
#
#
#        def on_data(fd, events):
#            try:
#                data = os.read(fd, 1024)
#                out_stream.send('scr %s' % data)
#                os.write(pty.STDOUT_FILENO, data)
#            except OSError:
#                ioloop.IOLoop.instance().stop()
#
#
#        def on_term_input(fd, events):
#            data = os.read(fd, 1024)
#            os.write(master_fd, data)
#            #log.write(data)
#            #log.flush()
#
#        buf = array.array('h', [0, 0, 0, 0])
#        fcntl.ioctl(pty.STDOUT_FILENO, termios.TIOCGWINSZ, buf, True)
#        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, buf)
#
#
#        mode = tty.tcgetattr(pty.STDIN_FILENO)
#        try:
#            try:
#                tty.setraw(pty.STDIN_FILENO)
#                restore = 1
#            except tty.error:    # This is the same as termios.error
#                restore = 0
#
#            in_stream.on_recv(on_message)
#
#            ioloop.IOLoop.instance().add_handler(master_fd, on_data, ioloop.IOLoop.READ)
#            ioloop.IOLoop.instance().add_handler(pty.STDIN_FILENO, on_term_input, ioloop.IOLoop.READ)
#            ioloop.IOLoop.instance().start()
#
#        finally:
#            os.close(master_fd)
#
#            if restore:
#                tty.tcsetattr(pty.STDIN_FILENO, tty.TCSAFLUSH, mode)
#
#            #log.close()
