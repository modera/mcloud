from copy import copy
import json
import os
from subprocess import Popen, PIPE


def list_git_ignore(dir_):
    lines = Popen(["git", "status", '-s', '--ignored'], stderr=PIPE, stdout=PIPE, cwd=dir_).communicate()[0]
    extra = ['.git']
    ignored = extra + [x.split(' ')[1] for x in lines.strip().split('\n') if x.startswith('!! ')]

    return ignored


def dump_node(path, relpath):
    return {
        '_path': relpath,
        '_is_dir': os.path.isdir(path),
        '_mtime': os.path.getmtime(path),
    }


def dump_file(dirname, ref, parts):

    if '_path' in ref:
        me = dump_node(os.path.join(dirname, ref['_path'], parts[0]), os.path.join(ref['_path'], parts[0]))
    else:
        me = dump_node(os.path.join(dirname, parts[0]), parts[0])

    ref[parts[0]] = me

    if len(parts) > 1:
        child = dump_file(dirname, ref[parts[0]], parts[1:])

        if child['_mtime'] > me['_mtime']:
            me['_mtime'] = child['_mtime']

    return me


def directory_snapshot(dirname):
    """
    Creates tree representing directory with recursive modification times

    :param dirname: Target directory
    :return:
    """

    dirname = os.path.realpath(dirname)

    struct = {}
    ignored = list_git_ignore(dirname)

    for root, dirs, files in os.walk(dirname):

        all_files = [os.path.join(root, f) for f in files] + [os.path.join(root, f) for f in dirs]

        for path_ in all_files:
            for ign in ignored:
                if path_.startswith(ign):
                    path_ = None
                    break

            if path_:
                path_ = path_[len(dirname) + 1:]
                dump_file(dirname, struct, path_.split(os.path.sep))

    return struct


def ref_path(ref):
    path_ = ref['_path']
    if ref['_is_dir']:
        path_ += '/'
    return path_


def merge_result(result, new_result):
    result['new'] += new_result['new']
    result['upd'] += new_result['upd']
    result['del'] += new_result['del']


def list_recursive(ref):
    ret = [ref_path(ref)]

    for name, sub in ref.items():
        if name.startswith('_'):
            continue
        ret += list_recursive(sub)

    return ret


def compare(src_struct, dst_struct):
    """
    Compare two directory snapshots returning list of new paths, removed paths, changed files.

    :param src:
    :param dest:
    :return:
    """

    result = {
        'new': [],
        'upd': [],
        'del': [],
    }

    for name, src in src_struct.items():
        if name.startswith('_'):
            continue

        if not name in dst_struct:
            result['new'] += list_recursive(src)
        else:
            dst = dst_struct[name]

            # updated
            if dst['_mtime'] < src['_mtime']:
                result['upd'].append(ref_path(src))

                merge_result(result, compare(src, dst))

    for name, dst in dst_struct.items():
        if not name in src_struct:
            result['del'].append(ref_path(dst))

    return result