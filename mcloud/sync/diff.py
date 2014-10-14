from subprocess import Popen, PIPE
from time import time
# from profilestats import profile
import sys
from scandir import scandir

import os


def is_ignored(ignore_list, path):
    for ign in ignore_list:

        if ign.endswith('/'):
            ign = ign[0:-1]

        if ign[0] == '*':
            return path.endswith(ign[1:])

        if path == ign:
            return True

        if path.startswith(ign + '/'):
            return True

    return False


def list_git_ignore(dir_):
    file_ = os.path.join(dir_, '.mcignore')

    if os.path.exists(file_):
        with open(file_) as f:
            patterns = [x.strip() for x in f.readlines() if x.strip() != '']
            return patterns
    else:
        return []


def dump_node(entry):

    return


def dump_file(dirname, ref, ignored, prefix='', ref_time=0):

    dirname.encode('utf-8')

    try:
        for entry in scandir(dirname):
            if entry.is_symlink():
                continue

            if is_ignored(ignored, entry.name):
                continue

            entry.name = entry.name.decode('utf-8')
            entry._directory = entry._directory.decode('utf-8')

            name = entry.name

            is_dir = entry.is_dir()

            if is_dir:
                name += '/'

            ref[name] = {
                '_path': prefix + name,
                '_mtime': ref_time - entry.stat().st_mtime,
            }

            if is_dir:
                dump_file(entry.path, ref[name], ignored, prefix=prefix + name, ref_time=ref_time)

            if prefix:
                if ref[name]['_mtime'] < ref['_mtime']:
                    ref['_mtime'] = ref[name]['_mtime']
    except OSError:
        sys.stderr.write('Warning: access denied: %s\n' % dirname)

# @profile
def directory_snapshot(dirname):

    """
    Creates tree representing directory with recursive modification times

    :param dirname: Target directory
    :return:
    """

    if not os.path.exists(dirname):
        return {}

    dirname = os.path.realpath(dirname)

    struct = {}
    ignored = list_git_ignore(dirname)

    dump_file(dirname, struct, ignored, ref_time=time())

    struct['_ignored'] = ignored

    return struct

def ref_path(ref):
    path_ = ref['_path']
    return path_


def merge_result(result, new_result):
    for type_ in ('new', 'upd', 'del'):
        result[type_] += new_result[type_]

def list_recursive(ref):
    ret = [ref_path(ref)]

    for name, sub in ref.items():
        if name.startswith('_'):
            continue
        ret += list_recursive(sub)

    return ret


def compare(src_struct, dst_struct, drift=0, ignored=None):
    """
    Compare two directory snapshots returning list of new paths, removed paths, changed files.

    :param src:
    :param dest:
    :return:
    """

    # print src_struct['.gitignore']
    # print dst_struct['.gitignore']

    if not ignored and '_ignored' in src_struct:
        ignored = src_struct['_ignored']

    result = {
        'new': [],
        'upd': [],
        'del': [],
    }

    for name, src in src_struct.items():
        if name.startswith('_'):
            continue

        # prevents removal of ignored on left side
        if ignored and is_ignored(ignored, src['_path']):
            continue

        if not name in dst_struct:
            result['new'] += list_recursive(src)
        else:
            dst = dst_struct[name]

            # updated
            if dst['_mtime'] > (drift + src['_mtime']):
                result['upd'].append(ref_path(src))

                merge_result(result, compare(src, dst, ignored=ignored))

    for name, dst in dst_struct.items():
        if name.startswith('_'):
            continue

        if ignored and is_ignored(ignored, dst['_path']):
            continue

        if not name in src_struct:
            result['del'].append(ref_path(dst))

    return result