from binascii import crc32
from filecmp import dircmp
from tempfile import NamedTemporaryFile
import os
import tarfile


def file_crc(path):
    crc = 0
    with open(path) as f:
        data = f.read(1024)
        while data != "":
            crc = crc32(data, crc)
            data = f.read(1024)
    return crc


def fileinfo(fname):
    """ when "file" tool is available, return it's output on "fname" """
    return (os.system('file 2> /dev/null') != 0 and
            os.path.exists(fname) and
            os.popen('file "' + fname + '"').read().strip().split(':')[1] )


def archive(base_path, paths):
    f = NamedTemporaryFile(delete=False)
    f.close()

    os.chdir(base_path)

    tar = tarfile.open(f.name, "w")
    for path in paths:
        tar.add(path, recursive=False)
    tar.close()

    return f.name


def unarchive(base_path, tar):
    os.chdir(base_path)

    tar = tarfile.open(tar)
    tar.extractall()

    tar.close()


def directories_synced(dir1, dir2, ignore=None):
    """
    Compare two local directories and print report.

    Used in tests.
    """
    if ignore:
        ignore = [x[0:-1] if x.endswith('/') else x for x in ignore]

    diff = dircmp(str(dir1), str(dir2), ignore, ignore)

    diff_size = len(diff.left_only) + len(diff.diff_files) + len(diff.right_only) + len(diff.funny_files)

    if diff_size > 0:

        print '\n' + '*' * 40 + '\n'
        print 'Diff report'
        print '\n' + '*' * 40 + '\n'
        print diff.report()
        print '\n' + '*' * 40 + '\n'

        return False

    return True

