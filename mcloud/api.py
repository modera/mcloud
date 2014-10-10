#!/usr/bin/python
import json

import sys
import socket
import os
from time import sleep

sleep(0.3)

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect('/var/run/mcloud')

args = []
if len(sys.argv) > 2:
    args = sys.argv[2:]

s.send(json.dumps({'hostname': os.uname()[1], 'command': sys.argv[1], 'args': args}))
data = json.loads(s.recv(1024 * 5))

s.close()

sys.exit(0 if data['status'] == 'ok' else 1)