from copy import copy
import json
import os
from subprocess import Popen, PIPE
from time import time
from pprintpp import pprint


def list_git_ignore(dir_):
    lines = Popen(["git", "status", '-s', '--ignored'], stderr=PIPE, stdout=PIPE, cwd=dir_).communicate()[0]
    extra = ['.git']
    ignored = extra + [x.split(' ')[1] for x in lines.strip().split('\n') if x.startswith('!! ')]

    return ignored


def dump_node(path, relpath):

    return {
        '_path': relpath,
        '_mtime': time() - os.path.getmtime(path),
    }


def dump_file(dirname, ref, parts):

    base_name = parts[0]

    if base_name == '':
        return

    if len(parts) > 1:
        base_name += '/'

    if not base_name in ref:
        if '_path' in ref:
            path_full = os.path.join(dirname, ref['_path'], base_name)
            path_rel = os.path.join(ref['_path'], base_name)
        else:
            path_full = os.path.join(dirname, base_name)
            path_rel = base_name

        # skip all links
        if os.path.islink(path_full):
            return

        me = dump_node(path_full, path_rel)

        ref[base_name] = me
    else:
        me = ref[base_name]

    if len(parts) > 1:
        child = dump_file(dirname, ref[base_name], parts[1:])

        if child:
            if child['_mtime'] < me['_mtime']:
                me['_mtime'] = child['_mtime']

    return me

from scandir import walk
from profilestats import profile

#@profile
def directory_snapshot(dirname):
    """
    Creates tree representing directory with recursive modification times

    :param dirname: Target directory
    :return:
    """

    dirname = os.path.realpath(dirname)

    struct = {}
    ignored = list_git_ignore(dirname)

    for root, dirs, files in walk(dirname):

        all_files = [os.path.join(root, f) + '/' for f in dirs] + [os.path.join(root, f) for f in files]

        for path_ in all_files:
            rel_path = path_[len(dirname) + 1:]
            for ign in ignored:
                if rel_path.startswith(ign):
                    path_ = None
                    break

            if path_:
                path_ = path_[len(dirname) + 1:]

                dump_file(dirname, struct, path_.split(os.path.sep))

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
            if dst['_mtime'] > src['_mtime']:
                result['upd'].append(ref_path(src))

                merge_result(result, compare(src, dst))

    for name, dst in dst_struct.items():
        if not name in src_struct:
            result['del'].append(ref_path(dst))

    return result