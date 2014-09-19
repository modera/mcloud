from shutil import copystat
from time import sleep
from mfcloud.volumes import directory_snapshot, compare


def test_snapshot(tmpdir):

    src = tmpdir.mkdir("src")
    src.join('boo.txt').write('123')
    src.mkdir('foo').join('boo.txt').write('123')

    ssrc = directory_snapshot(str(src))

    assert len(ssrc.values()) == 2
    assert ssrc['boo.txt']['_path'] == 'boo.txt'
    assert ssrc['foo']['_path'] == 'foo'
    assert ssrc['foo']['boo.txt']['_path'] == 'foo/boo.txt'


def test_compare(tmpdir):

    src = tmpdir.mkdir("src")
    dst = tmpdir.mkdir("dst")

    ssrc = directory_snapshot(str(src))
    sdst = directory_snapshot(str(dst))

    assert compare(ssrc, sdst) == {
        'new': [],
        'upd': [],
        'del': [],
    }


def test_compare_new_file(tmpdir):

    src = tmpdir.mkdir("src")
    dst = tmpdir.mkdir("dst")

    src.join('boo.txt').write('123')

    ssrc = directory_snapshot(str(src))
    sdst = directory_snapshot(str(dst))

    assert compare(ssrc, sdst) == {
        'new': ['boo.txt'],
        'upd': [],
        'del': [],
    }


def test_compare_later_modified_file(tmpdir):

    src = tmpdir.mkdir("src")
    dst = tmpdir.mkdir("dst")

    src.join('boo.txt').write('fsafsadfa')
    sleep(0.01)
    dst.join('boo.txt').write('dsdsds')  # written later

    ssrc = directory_snapshot(str(src))
    sdst = directory_snapshot(str(dst))

    assert compare(ssrc, sdst) == {
        'new': [],
        'upd': [],
        'del': [],
    }


def test_compare_not_modified_file(tmpdir):

    src = tmpdir.mkdir("src")
    dst = tmpdir.mkdir("dst")

    src.join('boo.txt').write('fsafsadfa')
    dst.join('boo.txt').write('dsdsds')


    ssrc = directory_snapshot(str(src))
    sdst = directory_snapshot(str(dst))

    sdst['boo.txt']['_mtime'] = ssrc['boo.txt']['_mtime']

    assert compare(ssrc, sdst) == {
        'new': [],
        'upd': [],
        'del': [],
    }


def test_compare_modified_file(tmpdir):

    src = tmpdir.mkdir("src")
    dst = tmpdir.mkdir("dst")

    dst.join('boo.txt').write('dsdsds')  # written earlier
    sleep(0.03)
    src.join('boo.txt').write('fsafsadfa')

    ssrc = directory_snapshot(str(src))
    sdst = directory_snapshot(str(dst))

    assert compare(ssrc, sdst) == {
        'new': [],
        'upd': ['boo.txt'],
        'del': [],
    }


def test_compare_removed_file(tmpdir):

    src = tmpdir.mkdir("src")
    dst = tmpdir.mkdir("dst")

    dst.join('boo.txt').write('dsdsds')

    ssrc = directory_snapshot(str(src))
    sdst = directory_snapshot(str(dst))

    assert compare(ssrc, sdst) == {
        'new': [],
        'upd': [],
        'del': ['boo.txt'],
    }


def test_compare_dirs(tmpdir):

    src = tmpdir.mkdir("src")
    dst = tmpdir.mkdir("dst")

    src.mkdir('foo')

    ssrc = directory_snapshot(str(src))
    sdst = directory_snapshot(str(dst))

    assert compare(ssrc, sdst) == {
        'new': ['foo/'],
        'upd': [],
        'del': [],
    }


def test_compare_recursive_new_dir(tmpdir):

    src = tmpdir.mkdir("src")
    dst = tmpdir.mkdir("dst")

    src.mkdir('foo').join('boo.txt').write('dsdsds')


    ssrc = directory_snapshot(str(src))
    sdst = directory_snapshot(str(dst))

    assert compare(ssrc, sdst) == {
        'new': ['foo/', 'foo/boo.txt'],
        'upd': [],
        'del': [],
    }


def test_compare_recursive_removed_dir(tmpdir):

    src = tmpdir.mkdir("src")
    dst = tmpdir.mkdir("dst")

    dst.mkdir('foo').join('boo.txt').write('dsdsds')


    ssrc = directory_snapshot(str(src))
    sdst = directory_snapshot(str(dst))

    assert compare(ssrc, sdst) == {
        'new': [],
        'upd': [],
        'del': ['foo/'],
    }


def test_compare_recursive_updated_dir(tmpdir):

    src = tmpdir.mkdir("src")
    dst = tmpdir.mkdir("dst")

    dst.mkdir('foo')
    sleep(0.01)
    src.mkdir('foo').join('boo.txt').write('dsdsds')

    ssrc = directory_snapshot(str(src))
    sdst = directory_snapshot(str(dst))

    assert compare(ssrc, sdst) == {
        'new': ['foo/boo.txt'],
        'upd': ['foo/'],
        'del': [],
    }


def test_compare_recursive_updated_dir_deeper(tmpdir):

    src = tmpdir.mkdir("src")
    dst = tmpdir.mkdir("dst")

    dst.join('bjaka.txt').write('dsdsds')  # removed file
    dst.mkdir('buka').join('buka.txt').write('dsdsds')  # removed dir
    dst.mkdir('foo').mkdir('boo').join('boo.txt').write('dsdsds')  # updated file
    sleep(0.01)
    src.mkdir('foo').mkdir('boo').join('boo.txt').write('dsdsds')  # update
    src.mkdir('bar').join('baz.txt').write('dsdsds')  # new directory with new file

    ssrc = directory_snapshot(str(src))
    sdst = directory_snapshot(str(dst))

    assert compare(ssrc, sdst) == {
        'new': ['bar/', 'bar/baz.txt'],
        'upd': ['foo/', 'foo/boo/', 'foo/boo/boo.txt'],
        'del': ['buka/', 'bjaka.txt'],
    }
