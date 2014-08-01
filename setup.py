from __future__ import print_function

import os
import sys
import imp

from setuptools import setup, find_packages


CODE_DIRECTORY = 'mfcloud'
DOCS_DIRECTORY = 'docs'
TESTS_DIRECTORY = 'tests'

# Import metadata. Normally this would just be:
#
#     from mfcloud import metadata
#
# However, when we do this, we also import `mfcloud/__init__.py'. If this
# imports names from some other modules and these modules have third-party
# dependencies that need installing (which happens after this file is run), the
# script will crash. What we do instead is to load the metadata module by path
# instead, effectively side-stepping the dependency problem. Please make sure
# metadata has no dependencies, otherwise they will need to be added to
# the setup_requires keyword.
metadata = imp.load_source(
    'metadata', os.path.join(CODE_DIRECTORY, 'metadata.py'))

# define install_requires for specific Python versions
python_version_specific_requires = []

# as of Python >= 2.7 and >= 3.2, the argparse module is maintained within
# the Python standard library, otherwise we install it as a separate package
if sys.version_info < (2, 7):
    python_version_specific_requires.append('argparse')


# See here for more options:
# <http://pythonhosted.org/setuptools/setuptools.html>
setup(
    name=metadata.package,
    version=metadata.version,
    author=metadata.authors[0],
    author_email=metadata.emails[0],
    maintainer=metadata.authors[0],
    maintainer_email=metadata.emails[0],
    url=metadata.url,
    description=metadata.description,
    long_description=open('README.rst').read(),
    # Find a list of classifiers here:
    # <http://pypi.python.org/pypi?%3Aaction=list_classifiers>
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Console',
        'Intended Audience :: Developers',
	    'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Documentation',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Software Distribution',
    ],
    packages=find_packages(exclude=(TESTS_DIRECTORY,)),
    install_requires=[
        'jinja2',
        'texttable',
        'twisted',
        'txredisapi',
        'inject',
        'voluptuous',
        'pprintpp',
        'prettytable',
        'docker-py',
        'treq',
        'pyOpenSSL',
        'PyYAML',
        'txsockjs',
        'service-identity',
        'netifaces',
        'dogapi',
        'autobahn==0.8.11',
        'pyasn1-modules',
        'characteristic',
        'confire',
    ] + python_version_specific_requires,
    # Allow tests to be run with `python setup.py test'.
    tests_require=[
        'pytest==2.5.1',
        'mock==1.0.1',
        'flake8==2.1.0',
    ],
    zip_safe=False,  # don't use eggs
    entry_points={
        'console_scripts': [
            'mfcloud = mfcloud.rpc_client:entry_point',
            'mfcloud-rpc-server = mfcloud.rpc_server:entry_point',
            'mfcloud-balancer = mfcloud.haproxy:entry_point',
            'mfcloud-dns = mfcloud.dns_resolver:entry_point',
            'mfcloud-websocket = mfcloud.websocket:entry_point',
            'mfcloud-uploader = mfcloud.upload_zip:entry_point',
        ],
        # if you have a gui, use this
        # 'gui_scripts': [
        #     'mfcloud_gui = mfcloud.gui:entry_point'
        # ]
    }

    # extras
    # 'Werkzeug'
    # 'Flask',
    # 'Flask-API',
    # 'pyunpack',s

)
