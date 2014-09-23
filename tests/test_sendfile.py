import os
from autobahn.twisted.util import sleep
from twisted.internet import reactor
from mfcloud.sendfile import FileServer, FileClient

import pytest

@pytest.inlineCallbacks
def test_file_upload(tmpdir):

    basedir = tmpdir.mkdir('foo')

    server = FileServer(basedir=str(basedir), host='localhost', port=33111)
    server.bind()

    yield sleep(0.01)

    baz = tmpdir.mkdir('baz')
    baz.join('boo.txt').write('test content')

    assert baz.join('boo.txt').read() == 'test content'

    client = FileClient(host='localhost', port=33111)
    yield client.upload('boo.txt', str(baz.join('boo.txt')), 123123)

    yield sleep(0.01)

    assert basedir.join('123123/boo.txt').exists()
    assert basedir.join('123123/boo.txt').size() > 0
    assert basedir.join('123123/boo.txt').read() == 'test content'


@pytest.inlineCallbacks
def test_file_download(tmpdir):

    basedir = tmpdir.mkdir('foo')
    basedir.join('boo.txt').write('here i am')

    server = FileServer(basedir=str(basedir), host='localhost', port=33112, file_resolver=lambda **_: str(basedir.join('boo.txt')))
    server.bind()

    yield sleep(0.01)

    baz = tmpdir.mkdir('baz')

    client = FileClient(host='localhost', port=33112, basedir=str(baz))
    yield client.download('boo.txt', app_name='hoho', ticket_id=321321)

    yield sleep(0.01)

    assert baz.join('321321/boo.txt').exists()
    assert baz.join('321321/boo.txt').read() == 'here i am'

