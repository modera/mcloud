# coding=utf-8
from mcloud.sync.diff import list_git_ignore
from mcloud.sync.server import FileServer
from mcloud.sync.utils import directories_synced
import os
from autobahn.twisted.util import sleep
from mcloud.sync.storage import  VolumeStorageLocal, get_storage, VolumeStorageRemote, storage_sync

import pytest
from flexmock import flexmock



def setup_function(function):
    function.cwd_before = os.getcwd()

def teardown_function(function):
    if os.getcwd() != function.cwd_before:
        pytest.fail('Function %s changes working directory. Was: %s Now: %s' % (function, function.cwd_before, os.getcwd()))


def test_get_storage_local():

    storage = get_storage('/foo/bar/baz')
    assert isinstance(storage, VolumeStorageLocal)

    assert storage.path == '/foo/bar/baz'


def test_get_storage_remote():

    storage = get_storage('baz.foo@example.com:/var/app')
    assert isinstance(storage, VolumeStorageRemote)

    assert storage.ref == {
        'service': 'baz',
        'app_name': 'foo',
        'volume': '/var/app',
    }
    assert storage.host == 'example.com'
    assert storage.port == 7081

def test_get_storage_remote_with_port():

    storage = get_storage('baz.foo@example.com:8888:/var/app')
    assert isinstance(storage, VolumeStorageRemote)

    assert storage.ref == {
        'service': 'baz',
        'app_name': 'foo',
        'volume': '/var/app',
    }
    assert storage.host == 'example.com'
    assert storage.port == 8888

def test_get_storage_remote_without_service():

    storage = get_storage('foo_bar@example.com')
    assert isinstance(storage, VolumeStorageRemote)

    assert storage.ref == {
        'app_name': 'foo_bar'
    }
    assert storage.host == 'example.com'
    assert storage.port == 7081

def test_get_storage_remote_without_service_me():

    storage = get_storage('foo@me')
    assert isinstance(storage, VolumeStorageRemote)

    assert storage.ref == {
        'app_name': 'foo'
    }
    assert storage.host == 'localhost'
    assert storage.port == 7081



@pytest.inlineCallbacks
def test_remote_volume_snapshot_with_storage(tmpdir):

    basedir = tmpdir.mkdir('foo')
    basedir.join('boo.txt').write('here i am')

    resolver = flexmock()
    resolver.should_receive('get_volume_path').with_args(app_name='hoho').and_return(str(basedir))

    server = FileServer(host='localhost', port=33113, file_resolver=resolver)
    server.bind()

    yield sleep(0.01)

    storage = get_storage('hoho@localhost:33113')
    snapshot = yield storage.get_snapshot()

    yield sleep(0.01)

    assert 'boo.txt' in snapshot
    assert snapshot['boo.txt']['_path'] == 'boo.txt'

    server.stop()


@pytest.inlineCallbacks
def test_storage_download_local(tmpdir):

    basedir = tmpdir.mkdir('foo')
    basedir.join('boo.txt').write('here i am')

    another = tmpdir.mkdir('baz')

    src = get_storage(str(basedir))

    yield src.download('boo.txt', str(another))

    assert another.join('boo.txt').exists()
    assert another.join('boo.txt').read() == 'here i am'

@pytest.inlineCallbacks
def test_storage_upload_local(tmpdir):

    basedir = tmpdir.mkdir('foo')
    basedir.join('boo.txt').write('here i am')

    another = tmpdir.mkdir('baz')

    src = get_storage(str(another))

    yield src.upload('boo.txt', str(basedir))

    assert another.join('boo.txt').exists()
    assert another.join('boo.txt').read() == 'here i am'


@pytest.inlineCallbacks
def test_storage_upload_local_non_existent_directory(tmpdir):

    basedir = tmpdir.mkdir('foo')
    basedir.join('boo.txt').write('here i am')

    another = tmpdir.mkdir('baz')

    src = get_storage(str(another) + '/123')

    yield src.upload('boo.txt', str(basedir))


    os.system('ls -la %s' % another)

    assert another.join('123/boo.txt').exists()
    assert another.join('123/boo.txt').read() == 'here i am'


@pytest.inlineCallbacks
def test_storage_upload_remote(tmpdir):

    basedir = tmpdir.mkdir('foo')
    basedir.join('boo.txt').write('here i am')

    another = tmpdir.mkdir('baz')

    resolver = flexmock()
    resolver.should_receive('get_volume_path').with_args(app_name='hoho').and_return(str(another))

    server = FileServer(host='localhost', port=33114, file_resolver=resolver)
    server.bind()

    storage = get_storage('hoho@localhost:33114')

    yield storage.upload(['boo.txt'], str(basedir))
    yield sleep(0.01)

    assert another.join('boo.txt').exists()
    assert another.join('boo.txt').read() == 'here i am'


@pytest.inlineCallbacks
def test_storage_download_remote(tmpdir):

    basedir = tmpdir.mkdir('foo')
    basedir.join('boo.txt').write('here i am')

    another = tmpdir.mkdir('baz')

    resolver = flexmock()
    resolver.should_receive('get_volume_path').with_args(app_name='hoho').and_return(str(basedir))

    server = FileServer(host='localhost', port=33115, file_resolver=resolver)
    server.bind()

    storage = get_storage('hoho@localhost:33115')

    yield storage.download('boo.txt', str(another))
    yield sleep(0.01)

    assert another.join('boo.txt').exists()
    assert another.join('boo.txt').read() == 'here i am'

@pytest.inlineCallbacks
def test_storage_remove_remote(tmpdir):

    basedir = tmpdir.mkdir('foo')
    basedir.join('boo.txt').write('here i am')

    resolver = flexmock()
    resolver.should_receive('get_volume_path').with_args(app_name='hoho').and_return(str(basedir))

    server = FileServer(host='localhost', port=33215, file_resolver=resolver)
    server.bind()

    storage = get_storage('hoho@localhost:33215')

    assert basedir.join('boo.txt').exists()

    yield storage.remove('boo.txt')
    yield sleep(0.01)

    assert not basedir.join('boo.txt').exists()



@pytest.inlineCallbacks
def test_storage_sync_local_to_local(tmpdir):

    basedir = tmpdir.mkdir('foo')
    basedir.join('boo.txt').write('here i am')

    another = tmpdir.mkdir('baz')
    another.join('hoho.txt').write('here i am')

    src = get_storage(str(basedir))
    dst = get_storage(str(another))

    yield storage_sync(src, dst, remove=True)

    assert directories_synced(basedir, another)


@pytest.inlineCallbacks
def test_storage_sync_remote_to_remote(tmpdir):

    remote1 = tmpdir.mkdir('remote1')
    remote1.join('boo.txt').write('here i am')

    remote2 = tmpdir.mkdir('remote2')
    remote2.join('hoho.txt').write('here i am')

    resolver1 = flexmock()
    resolver1.should_receive('get_volume_path').with_args(app_name='hoho').and_return(str(remote1))

    server1 = FileServer(host='localhost', port=33116, file_resolver=resolver1)
    server1.bind()

    resolver2 = flexmock()
    resolver2.should_receive('get_volume_path').with_args(app_name='hoho').and_return(str(remote2))

    server2 = FileServer(host='localhost', port=33117, file_resolver=resolver2)
    server2.bind()

    src = get_storage('hoho@localhost:33116')
    dst = get_storage('hoho@localhost:33117')

    yield storage_sync(src, dst, remove=True)

    assert directories_synced(remote1, remote2)


@pytest.inlineCallbacks
def test_storage_sync_remote_to_local(tmpdir):

    remote1 = tmpdir.mkdir('remote1')
    remote1.join('boo.txt').write('here i am')

    resolver1 = flexmock()
    resolver1.should_receive('get_volume_path').with_args(app_name='hoho').and_return(str(remote1))

    server1 = FileServer(host='localhost', port=33118, file_resolver=resolver1)
    server1.bind()

    another = tmpdir.mkdir('baz')
    another.join('hoho.txt').write('here i am')

    src = get_storage('hoho@localhost:33118')
    dst = get_storage(str(another))

    yield storage_sync(src, dst, remove=True)

    assert directories_synced(remote1, another)


@pytest.inlineCallbacks
def test_storage_sync_local_to_remote(tmpdir):

    another = tmpdir.mkdir('baz')
    another.join('boo.txt').write('here i am')

    remote1 = tmpdir.mkdir('remote1')
    remote1.join('hoho.txt').write('here i am')

    resolver1 = flexmock()
    resolver1.should_receive('get_volume_path').with_args(app_name='hoho').and_return(str(remote1))

    server1 = FileServer(host='localhost', port=33119, file_resolver=resolver1)
    server1.bind()

    src = get_storage(str(another))
    dst = get_storage('hoho@localhost:33119')

    yield storage_sync(src, dst, remove=True)

    assert directories_synced(another, remote1)

@pytest.inlineCallbacks
def test_storage_sync_big_file_local_to_remote(tmpdir):

    another = tmpdir.mkdir('baz')

    # generate 20 mb file
    with open(str(another.join('boo.txt')), 'w+') as f:
        for i in range(1, 1024 * 20):
            f.write(os.urandom(1024))

    remote1 = tmpdir.mkdir('remote1')
    remote1.join('hoho.txt').write('here i am')

    resolver1 = flexmock()
    resolver1.should_receive('get_volume_path').with_args(app_name='hoho').and_return(str(remote1))

    server1 = FileServer(host='localhost', port=33120, file_resolver=resolver1)
    server1.bind()

    src = get_storage(str(another))
    dst = get_storage('hoho@localhost:33120')

    yield storage_sync(src, dst, remove=True)

    assert directories_synced(another, remote1)


@pytest.inlineCallbacks
def test_storage_sync_lot_of_files_local_to_remote(tmpdir):

    another = tmpdir.mkdir('baz')

    # generate 20 mb file
    for i in range(1, 2000):
        with open(str(another.join('hoho_%s.txt' % i)), 'w+') as f:
            f.write(os.urandom(128))

    remote1 = tmpdir.mkdir('remote1')
    remote1.join('hoho.txt').write('here i am')


    resolver1 = flexmock()
    resolver1.should_receive('get_volume_path').with_args(app_name='hoho').and_return(str(remote1))

    server1 = FileServer(host='localhost', port=33220, file_resolver=resolver1)
    server1.bind()

    src = get_storage(str(another))
    dst = get_storage('hoho@localhost:33220')

    yield storage_sync(src, dst, remove=True)

    assert directories_synced(another, remote1)
a