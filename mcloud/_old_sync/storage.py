from distutils.dir_util import copy_tree
import pipes
import pydoc
from shutil import rmtree, copy
from tempfile import mkdtemp
from time import time
import shutil
from mcloud.application import Application
from mcloud.sync.client import FileClient
from mcloud.sync.diff import directory_snapshot, compare
from mcloud.util import query_yes_no
import os
import re
from twisted.internet.defer import inlineCallbacks
from twisted.python import log


def _remove_path(real_path):
    if os.path.isdir(real_path):
        rmtree(real_path)
    else:
        os.unlink(real_path)

class VolumeStorageRemote(object):
    def __init__(self, host, port, **ref):
        super(VolumeStorageRemote, self).__init__()

        self.ref = ref
        for key, val in ref.items():
            if val is None:
                del ref[key]

        if host == 'me':
            host = 'localhost'

        self.host = host
        self.port = port

        self.last_snapshot_id = None

    def _get_client(self):
        return FileClient(host=self.host, port=self.port)

    def get_snapshot(self):
        return self._get_client().snapshot(**self.ref)


    @inlineCallbacks
    def upload(self, paths, base_dir):
        yield self._get_client().upload(paths, base_dir, **self.ref)

    @inlineCallbacks
    def download(self, paths, base_dir):
        yield self._get_client().download(paths, base_dir, **self.ref)

    @inlineCallbacks
    def remove(self, path):
        yield self._get_client().remove(path=path, **self.ref)



class VolumeStorageLocal(object):
    def __init__(self, path):
        super(VolumeStorageLocal, self).__init__()

        self.path = os.path.realpath(path)


    def get_snapshot(self):
        return directory_snapshot(self.path)

    def sync(self, volume_diff, source):

        for path in volume_diff['new']:
            self.upload(os.path.join(source.path, path), path)

        for path in volume_diff['upd']:
            self.upload(os.path.join(source.path, path), path)

        for path in volume_diff['del']:
            self.remove(path)

    def _do_copy(self, src_path, target_path):

        if target_path.endswith('/'):
            if not os.path.exists(target_path):
                os.makedirs(target_path)
        else:
            if not os.path.exists(os.path.dirname(target_path)):
                os.makedirs(target_path)

            if os.path.exists(target_path):
                _remove_path(target_path)

            copy(src_path, target_path)

    def download(self, paths, base_dir):
        if not isinstance(paths, list) and not isinstance(paths, tuple):
            paths = [paths]

        for path in paths:
            src_path = os.path.join(self.path, path)
            target_path = os.path.join(base_dir, path)

            self._do_copy(src_path, target_path)

    def upload(self, paths, base_dir):
        # if not isinstance(paths, list) and not isinstance(paths, tuple):
        #     paths = [paths]

        if not base_dir.endswith('/'):
            base_dir += '/'

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        copy_tree(pipes.quote(base_dir), pipes.quote(self.path), preserve_symlinks=True)

    def remove(self, path):
        real_path = os.path.join(self.path, path)
        if real_path.endswith('/'):
            real_path = real_path[0:-1]
        _remove_path(real_path)



def print_diff(volume_diff):
    cnt = 0
    diff = ''
    for type_, label in (('new', 'New'), ('upd', 'Updated'), ('del', 'Removed'), ):
        if volume_diff[type_]:
            diff += '\n\n'
            diff += '\n%s\n' % label + '-' * 40

            for file_ in volume_diff[type_]:
                cnt += 1
                diff += '\n   - ' + file_

    return cnt, diff

def diff_has_changes(volume_diff):
    return volume_diff['new'] or volume_diff['upd'] or volume_diff['del']

@inlineCallbacks
def storage_sync(src, dst, confirm=False, verbose=False, remove=False, full=True):

    tmp_path = mkdtemp()

    try:
        print 'Download'
        yield src.download(paths_to_upload, tmp_path)
        print 'Upload'
        yield dst.upload(paths_to_upload, tmp_path)

    finally:
        if len(paths_to_upload):
            rmtree(tmp_path)
        pass

    for path in volume_diff['del']:
        print('Removing %s' % path)
        yield dst.remove(path)


    print('\nDone.')
