#!/bin/sh
''''which python >/dev/null && exec /usr/bin/env python "$0" "$@" # '''
''''which python2 >/dev/null && exec /usr/bin/env python2 "$0" "$@" # '''
''''which python3 >/dev/null && exec /usr/bin/env python3 "$0" "$@" # '''

import sys

print("\n@mcloud %s\n" % ' '.join(sys.argv[1:]))

sys.exit(0)