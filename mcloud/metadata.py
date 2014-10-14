"""Project metadata

Information describing the project.
"""
import os
from mcloud.version import version as mcloud_version

root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# The package name, which is also the "UNIX name" for the project.
package = 'mcloud'
project = "mcloud"
project_no_spaces = project.replace(' ', '')
version = mcloud_version
description = 'A tool that helps you manage Docker based deployments'
authors = ['Alex Rudakov']
authors_string = ', '.join(authors)
emails = ['ribozz@gmail.com']
license = 'Apache License'
copyright = '2013 ' + authors_string
url = 'http://mcloud.io/'
