import os
from mcloud.sync.utils import archive, unarchive, directories_synced


def test_archive_unarchive(tmpdir):

    baz = tmpdir.mkdir('baz')
    baz.join('boo.txt').write('test content')
    baz.mkdir('foo').join('baz.txt').write('test content')

    tar = archive(str(baz), ['boo.txt', 'foo/', 'foo/baz.txt'])

    assert os.path.exists(tar)

    boo = tmpdir.mkdir('boo')
    unarchive(str(boo), tar)

    assert directories_synced(str(boo), str(baz))
