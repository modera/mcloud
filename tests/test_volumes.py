import os
from shutil import copystat
from time import sleep
from pprintpp import pprint
from mfcloud.volumes import directory_snapshot, compare, is_ignored
import pytest

def test_snapshot(tmpdir):

    src = tmpdir.mkdir("src")
    src.join('boo.txt').write('123')
    src.mkdir('foo').join('boo.txt').write('123')

    ssrc = directory_snapshot(str(src))

    pprint(ssrc)

    assert len(ssrc.values()) == 2
    assert len(ssrc['foo/'].values()) == 3  # mtime is added here
    assert ssrc['boo.txt']['_path'] == 'boo.txt'
    assert ssrc['foo/']['_path'] == 'foo/'
    assert ssrc['foo/']['boo.txt']['_path'] == 'foo/boo.txt'


    assert '_path' not in ssrc


def test_snapshot_no_dir(tmpdir):

    with pytest.raises(ValueError):
        directory_snapshot('boooooo')


def test_simple_compare(tmpdir):

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

def test_compare_new_file_gitignore(tmpdir):

    src = tmpdir.mkdir("src")
    dst = tmpdir.mkdir("dst")

    os.chdir(str(src))
    os.system('git init')
    src.join('boo.txt').write('123')
    src.join('boo2.txt').write('123')
    src.join('.gitignore').write('boo2.txt')

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
    sleep(0.1)
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

    print ssrc
    print sdst

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


def test_compare_recursive_updated__dir(tmpdir):

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
        'del': ['bjaka.txt', 'buka/'],
    }


def test_ignore():

    ignore_list = ['.git/', '.env/']

    assert not is_ignored(ignore_list, '.gitignore')
    assert not is_ignored(ignore_list, '.gitmodules')

    assert is_ignored(ignore_list, '.git')
    assert is_ignored(ignore_list, '.git/')
    assert is_ignored(ignore_list, '.git/foo')

    assert is_ignored(ignore_list, '.env/lib/python2.7/site-packages/_pytest/pastebin.py')