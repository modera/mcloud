#!/bin/sh
''''which python >/dev/null && exec /usr/bin/env python "$0" "$@" # '''
''''which python2 >/dev/null && exec /usr/bin/env python2 "$0" "$@" # '''
''''which python3 >/dev/null && exec /usr/bin/env python3 "$0" "$@" # '''

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

s.send(json.dumps({'hostname': os.uname()[1], 'command': sys.argv[1], 'args': args}).encode('utf-8'))
data = json.loads(s.recv(1024 * 5).decode('utf-8'))

s.close()

sys.exit(0 if data['status'] == 'ok' else 1)