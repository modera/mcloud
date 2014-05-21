from __future__ import unicode_literals

from subprocess import Popen, PIPE, STDOUT
import re
import datetime
import os

from pyunpack import Archive


EXTRACT_DIR = '/path/'


# use archive file
class ArchiveFile:

    # init filename
    def __init__(self, filename, path_extract):
        self.filename = filename
        global EXTRACT_DIR
        EXTRACT_DIR = path_extract

    # get type archive
    def type(self):
        out = Popen('7za l {0}'.format(self.filename),
                    shell=True,
                    stdout=PIPE,
                    stderr=STDOUT)
        text = out.stdout.read()
        pattern = re.compile('Type\s\=\s(\S+)\s')
        match = re.search(pattern, text)
        if match:
            _type = match.group(1)
            if _type == '7z':
                solid = re.search('Solid\s\=\s(\S)\s', text)
                if solid.group(1) == '+':
                    return '7z'
                else:
                    return 'tar7z'
            return _type
        return 'file_obj'

    # get prepare list
    def prepare(self):
        out = Popen('7za l {0}'.format(self.filename),
                    shell=True,
                    stdout=PIPE,
                    stderr=STDOUT)
        lines = out.stdout.readlines()
        string = lines[len(lines) - 1]
        pattern = re.compile('\s*(\d+)\s*(\d+)\s*(\d+) files, (\d+) folders')
        result = re.search(pattern, string)
        if result:
            return {'folders': int(result.group(4)),
                    'files': int(result.group(3)),
                    'size': int(result.group(1))}
        else:
            return {'folders': 0,
                    'files': 0,
                    'size': 0}

    # get list dir
    def list_dir(self, path):
        return os.listdir(path)

    # extract files
    def extract(self):
        try:
            folder = 'unzip'
            path = '{0}{1}/'.format(EXTRACT_DIR, folder)
            if not os.path.exists(path):
                os.makedirs(path)

            Archive(self.filename).extractall(path)
            result = []
            for file in self.list_dir(path):
                if file != '__MACOSX':
                    result.append({'orig_name': str(file),
                                   'result_link': '{0}{1}'.format(path, file),
                                   'folder': folder,
                                   'filename': file})
            return result
        except:
            return False
