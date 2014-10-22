

===================================
Installation on linux
===================================

Instructions are given for Ubuntu linux, but except some details, like
package names and file-system paths, process is same on all operating systems.

What will be installed?
===========================

Install sh does:

- Installs mcloud && haproxy ppa keys
- install mcloud-full package

mcloud-full package contains:

- mcloud's binary files
- docker.io
- redis-server
- haproxy (NB! mclouds overrides /haproxy on first start)
- dnsmasq (NB! mclouds override /etc/dnsmasq.conf on post-install)

If you are not agree with this changes, you can install *mcloud* package instead :ref:`manual_install`

Mcloud installation
==========================

.. note::
    Currently we provide packages for all current version of Ubuntu trusty(14.04), precise(12.04) and lucid(10.04).
    If you need to install mcloud on other OS, install it from source: :ref:`from_source`


Install mcloud-full::

    curl https://mcloud.io/install.sh |sudo sh


Checking installation
=======================================

Just start mcloud shell::

    $ mcloud

    mcloud: ~@me>

Hit Ctrl+D to exit mcloud shell.