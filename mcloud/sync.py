from copy import copy
import inject
import os
import subprocess
from mcloud.application import Application
import re
# from mcloud.application import Application
from twisted.internet import inotify
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.inotify import INotify, IN_CREATE, IN_MODIFY, IN_MOVED_TO
from twisted.python import filepath


class VolumeNotFound(ValueError):
    pass

def get_storage(ref):
    match = re.match('^((%(app_regex)s)\.)?(%(service_regex)s)@([a-z0-9A-Z\-\.]+)(:([0-9]+))?(:(.*))?$' % {
        'app_regex': Application.APP_REGEXP,
        'service_regex': Application.SERVICE_REGEXP,
    }, ref)
    if match:
        service = match.group(2)
        app = match.group(3)
        host = match.group(4)
        volume = match.group(8)

        if host == 'me':
            host = '127.0.0.1'

        # if not re.match('^[0-9\.]+$', host):
        #     host = BlockingResolver().getHostByName(host)

        return 'remote', (host, app, service, volume)
    else:
        return 'local', (ref,)

class BlockingINotifyWatcher(INotify):

    defered = None

    def connectionLost(self, reason):
        self.defered.callback(reason)

    def block(self):
        self.defered = Deferred()
        return self.defered



@inlineCallbacks
def rsync_folder(client, src_args, dst_args, reverse=False, options=None):

    if not options:
        options = {}

    (host, app, service, volume) = src_args

    if volume and volume.endswith('/'):
        volume = volume[:-1]

    with client.override_host(host):
        data = yield client._remote_exec('sync', app, service, volume)

    try:
        dst_dir = dst_args[0]

        src_ref = 'rsync://%s@%s:%s/data%s/' % (data['env']['USERNAME'], host, data['port'], data['volume'])

        if 'path' in options and not options['path'] is None:
            src_ref = os.path.join(src_ref, options['path'])
            dst_dir = os.path.join(dst_dir, options['path'])
        else:
            if not src_ref.endswith('/'):
                src_ref += '/'

        # rsync requires "/" at the end
        if os.path.isdir(dst_dir) and not dst_dir.endswith('/'):
            dst_dir += '/'

        env = {
            'RSYNC_PASSWORD': data['env']['PASSWORD']
        }

        command = ['rsync']

        command.append('--recursive')
        command.append('--links')  # only links from same directory
        command.append('--perms')  # keep permissions
        command.append('--times')  # keep modification time
        command.append('--numeric-ids')  # keep file ownership
        command.append('--human-readable')  # human readable numbers

        ignore_file = os.path.join(dst_dir, '.mcignore')
        if os.path.exists(ignore_file):
            command.append('--exclude-from=%s' % ignore_file)  # keep modification time

        raw_command = copy(command)

        command.append('--verbose')

        # if not 'no_remove' in options or options['no_remove'] is False:
        #     command.append('--delete')  # remove files if missing in source
        #     command.append('--delete-excluded')  # allow deletion of excluded files

        if 'update' in options and options['update'] is True:
            command.append('--update')  # partial update

        if not reverse:
            command.append(src_ref)
            command.append(dst_dir)
        else:
            command.append(dst_dir)
            command.append(src_ref)

        process = subprocess.Popen(command, env=env)
        process.wait()

        if 'watch' in options and options['watch'] is True:

            raw_command.append('--update')

            if not reverse:
                raise Exception('Can not watch remote volume.')

            watch_dir = os.path.realpath(dst_dir)
            print watch_dir
            def notify(self, filepath, mask):
                filepath = filepath.realpath().path[len(watch_dir) + 1:]
                if not filepath.endswith('___jb_bak___') and not filepath.endswith('___jb_old___'):
                    print "%s> %s" % (', '.join(inotify.humanReadableMask(mask)), filepath)

                    new_cmd = raw_command + [os.path.join(dst_dir, filepath), os.path.join(src_ref, filepath)]
                    process = subprocess.Popen(new_cmd, env=env)
                    process.wait()

            notifier = BlockingINotifyWatcher()
            notifier.startReading()
            notifier.watch(filepath.FilePath(dst_dir), callbacks=[notify], recursive=True,
                           mask=IN_CREATE | IN_MODIFY | IN_MOVED_TO)

            class SyncInterruptHandler(object):

                @inlineCallbacks
                def interrupt(self, last=None):
                    yield client._remote_exec('sync_stop', app, data['ticket_id'])

            interrupt_manager = inject.instance('interrupt_manager')
            interrupt_manager.append(SyncInterruptHandler())

            yield notifier.block()

    finally:

        with client.override_host(host):
            yield client._remote_exec('sync_stop', app, data['ticket_id'])