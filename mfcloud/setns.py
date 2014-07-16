from mfcloud.syscall import set_ns, CLONE_NEWUTS
import os

pid = '30116'
namespace_dir = os.path.join('/proc', pid, 'ns')
for namespace in ['uts', 'pid', 'net', 'ipc', 'mnt']:
    path = os.path.join(namespace_dir, namespace)
    print path
    with open(path) as f:
        set_ns(f)
        os.execvp('/bin/bash', ['/bin/bash'])