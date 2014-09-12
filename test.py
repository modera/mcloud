
import sys, socket;s=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM);s.connect('/var/run/mfcloud');s.send('[boo] %s' % sys.stdin.read().strip());s.close()
