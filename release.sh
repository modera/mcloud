#!/bin/bash -e

pip install -e .
pip install -r requirements-dev.txt
py.test tests

VERSION=`python release.py`

if [ $VERSION = "0" ]; then
    echo "Version already deployed."
    exit 0;
fi

echo "version = '$VERSION'" > mcloud/version.py

#dpkg-buildpackage -us -uc

python setup.py sdist register upload

git push --tags
