# coding=utf-8
from flexmock import flexmock
from mfcloud.sync.client import FileClient
from mfcloud.sync.server import FileServer
from mfcloud.sync.transfer import CrcCheckFailed
import os
from autobahn.twisted.util import sleep
import pytest


@pytest.inlineCallbacks
def test_file_upload(tmpdir):

    basedir = tmpdir.mkdir('foo')

    resolver = flexmock()
    resolver.should_receive('get_volume_path').with_args(app_name="hoho").and_return(str(basedir))

    server = FileServer(host='localhost', port=33111, file_resolver=resolver)
    server.bind()

    yield sleep(0.01)

    baz = tmpdir.mkdir('baz')
    baz.join('boo.txt').write('test content')

    assert baz.join('boo.txt').read() == 'test content'

    client = FileClient(host='localhost', port=33111)
    yield client.upload(['boo.txt'], str(baz), app_name='hoho')

    yield sleep(0.01)

    assert basedir.join('boo.txt').exists()
    assert basedir.join('boo.txt').size() > 0
    assert basedir.join('boo.txt').read() == 'test content'

    server.stop()

@pytest.inlineCallbacks
def test_file_upload_bad_crc(tmpdir, monkeypatch):

    basedir = tmpdir.mkdir('foo')

    resolver = flexmock()
    resolver.should_receive('get_volume_path').with_args(app_name="hoho").and_return(str(basedir))

    server = FileServer(host='localhost', port=33211, file_resolver=resolver)
    server.bind()

    yield sleep(0.01)

    baz = tmpdir.mkdir('baz')
    baz.join('boo.txt').write('test content')

    assert baz.join('boo.txt').read() == 'test content'

    client = FileClient(host='localhost', port=33211)
    monkeypatch.setattr(client, 'file_crc', lambda path: 'invalid-crc')

    with pytest.raises(CrcCheckFailed):
        yield client.upload(['boo.txt'], str(baz), app_name='hoho')

    server.stop()


@pytest.inlineCallbacks
def test_file_download(tmpdir):

    basedir = tmpdir.mkdir('foo')
    basedir.join('boo.txt').write('here i am')

    resolver = flexmock()
    resolver.should_receive('get_volume_path').with_args(app_name="hoho").and_return(str(basedir))

    server = FileServer(host='localhost', port=33112, file_resolver=resolver)
    server.bind()

    yield sleep(0.01)

    baz = tmpdir.mkdir('baz')

    client = FileClient(host='localhost', port=33112)
    yield client.download(['boo.txt'], str(baz), app_name='hoho')

    yield sleep(0.01)

    assert baz.join('boo.txt').exists()
    assert baz.join('boo.txt').read() == 'here i am'

    server.stop()



@pytest.inlineCallbacks
def test_remote_snapshot_unicode(tmpdir):
    resolver = flexmock()
    resolver.should_receive('get_volume_path').with_args(app_name='hoho').and_return(os.path.dirname(__file__) + '/_files/snap_unicode')

    server = FileServer(host='localhost', port=33112, file_resolver=resolver)
    server.bind()

    yield sleep(0.01)

    client = FileClient(host='localhost', port=33112)
    snapshot = yield client.snapshot(app_name='hoho')

    yield sleep(0.01)

    filename = u'хуйюй мухуюй.txt'
    assert filename in snapshot
    assert snapshot[filename]['_path'] == filename

    server.stop()

@pytest.inlineCallbacks
def test_remote_snapshot(tmpdir):

    basedir = tmpdir.mkdir('foo')
    basedir.join('boo.txt').write('here i am')

    print 'Brfore snapshot'

    resolver = flexmock()
    resolver.should_receive('get_volume_path').with_args(app_name='hoho').and_return(str(basedir))



    server = FileServer(host='localhost', port=33112, file_resolver=resolver)
    server.bind()



    yield sleep(0.01)

    client = FileClient(host='localhost', port=33112)

    snapshot = yield client.snapshot(app_name='hoho')

    yield sleep(0.01)

    assert 'boo.txt' in snapshot
    assert snapshot['boo.txt']['_path'] == 'boo.txt'

    server.stop()

