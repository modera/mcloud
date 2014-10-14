"""Project metadata

Information describing the project.
"""
import os

root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# The package name, which is also the "UNIX name" for the project.
package = 'mcloud'
project = "mcloud"
project_no_spaces = project.replace(' ', '')
version = '0.6.1'
description = 'Production cloud deployments of fig infrastructure with docker'
authors = ['Alex Rudakov']
authors_string = ', '.join(authors)
emails = ['ribozz@gmail.com']
license = 'Apache License'
copyright = '2013 ' + authors_string
url = 'http://pywizard.com/mcloud/'
