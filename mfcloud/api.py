#!/usr/bin/python

import sys
import socket
import os


data = ' '.join(sys.argv[1:])

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect('/var/run/mfcloud')
s.send('[%s] %s' % (os.uname()[1], data))
code = s.recv(3)
data = s.recv(1024 * 5)
print data
s.close()

sys.exit(0 if code == 'ok|' else 1)