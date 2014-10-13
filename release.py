
"""
Implement following release procedure:

- Take name of current branch 0.X
- Create a new tag with name 0.X.Y (by incrementing last digit)
- dump CHANGELOG.txt file
- update debian changelog
- build and upload package to pypi
- build debian package and add id to debian repo

"""

import argparse
import datetime
import pipes
import os
import re
from git import Repo
import sys


def match_versioning_branch_format(name):
    if not hasattr(match_versioning_branch_format, 're'):
        match_versioning_branch_format.re = re.compile('^\d+\.\d+$')
    return match_versioning_branch_format.re.match(name)


def find_latest_tag(repo, branch_name):

    preg = re.compile('^%s\.(\d+)$' % re.escape(branch_name))

    tags_found = {}
    for ref in repo.tags:
        result = preg.match(ref.tag.tag)
        if result:
            tags_found[int(result.group(1))] = ref

    if len(tags_found) == 0:
        return 0, None

    max_key = max(tags_found.keys())

    return max_key, tags_found[max_key]


def file_prepend(filename, data):
    f = open(filename, 'r')
    temp = f.read()
    f.close()
    f = open(filename, 'w')
    f.write(data)
    f.write(temp)
    f.close()


if __name__ == "__main__":

    repo = Repo(".")
    repo.remotes.origin.fetch()

    branch_name = repo.active_branch.name
    if not match_versioning_branch_format(branch_name):
        sys.stderr.write("Current branch doesn't seem to be correct version format '%%d.%%d' : %s \n" % branch_name)
        exit(1)

    max_key, ref = find_latest_tag(repo, branch_name)

    if not ref or ref.commit.hexsha != repo.head.commit.hexsha:
        new_tag_name = '%s.%d' % (branch_name, max_key + 1)
        new_ref = repo.create_tag(new_tag_name, message='New version: %s' % new_tag_name)


        os.chdir('debian')
        logs = []

        if ref:
            for commit in repo.iter_commits('%s..%s' % (ref.tag.tag, new_tag_name)):
                message = commit.message.strip()
                os.system('dch -v %s-1 %s' % (new_tag_name, message))
                logs.append(message)
            # os.system('dch -r')

            data = '%s %s\n    *%s\n\n' % (new_tag_name, datetime.datetime.now().isoformat(), '\n\t    *'.join(logs))

            os.chdir('../')

            file_prepend('CHANGES.txt', data)

        sys.stdout.write(new_ref.tag.tag)

    else:

        sys.stdout.write('0')
