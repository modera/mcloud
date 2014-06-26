
============================================
mfcloud installation
============================================

Instructions are given for Ubuntu linux, but except some details, like
package names and file-system paths, process is same on all operating systems.

Prerequisites
===============

Uodate package cache::

    sudo apt-get update

Install redis::

    sudo apt-get install redis-server

Required packages::

    sudo apt-get install python-dev python-virtualenv libffi-dev libssl-dev

Package installation
========================================

Install mfcloud packages::

    sudo mkdir /opt  # if you don't have it already
    sudo virtualenv /opt/mfcloud
    sudo /opt/mfcloud/bin/pip install mfcloud

Link mfcloud executables::

    sudo ln -s /opt/mfcloud/bin/mfcloud* /usr/local/bin/


Now you can run mfcloud-rpc-server.

Running mfcloud-server with supervisor
===========================================

Install supervisor::

    apt-get install supervisor

Create filr /etc/supervisor/conf.d/mfcloud.conf with following contents::

    [program:mfcloud]
    command=/opt/mfcloud/bin/mfcloud-rpc-servers

Start service::

    sudo supervisorctl start mfcloud


Running mfcloud-server with upstart
===========================================

Create file /etc/init/mfcloud.conf with follwing contents::

    exec /opt/mfcloud/bin/mfcloud-rpc-servers

Run mfcloud serive::

    sudo service mfcloud start

