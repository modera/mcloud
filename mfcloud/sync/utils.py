from binascii import crc32
from filecmp import dircmp
from tempfile import NamedTemporaryFile
from mfcloud.util import safe_chdir
import os
import tarfile

class VolumeNotFound(ValueError):
    pass

def file_crc(path, buffer_size=1024):
    """
    Calculates cumulative file crc32 by reading it by blocks of size specified.

    :param buffer_size: Amount of block for loading into memory.
    :param path:
    :return:
    """
    crc = 0
    with open(path) as f:
        data = f.read(buffer_size)
        while data != "":
            crc = crc32(data, crc)
            data = f.read(buffer_size)
    return crc


def fileinfo(fname):
    """ when "file" tool is available, return it's output on "fname" """
    return (os.system('file 2> /dev/null') != 0 and
            os.path.exists(fname) and
            os.popen('file "' + fname + '"').read().strip().split(':')[1] )


def archive(base_path, paths):
    """
    Creates archive in temporary directory with files specified
     and returns filename of resulting archive.

    :param base_path: Root path
    :param paths: files to archive
    :return:
    """
    f = NamedTemporaryFile(delete=False)
    f.close()

    with safe_chdir(base_path):

        tar = tarfile.open(f.name, "w")
        for path in paths:
            tar.add(path, recursive=False)
        tar.close()

    return f.name


def unarchive(base_path, tar):
    """
    Extract archive into folder specified.

    :param base_path:
    :param tar: Full file-path
    """
    with safe_chdir(base_path):

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

