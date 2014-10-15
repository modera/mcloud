

===================================
Installation on linux
===================================

Instructions are given for Ubuntu linux, but except some details, like
package names and file-system paths, process is same on all operating systems.

What will be installed?
===========================

mcloud-full package installs:

- mcloud's binary files
- docker.io
- redis-server
- haproxy (NB! mclouds overrides /haproxy on first start)
- dnsmasq (NB! mclouds override /etc/dnsmasq.conf on post-install)

If you are not agree with this changes, you can install *mcloud* package instead :ref:`manual_install`

Mcloud installation
==========================

.. note::
    Currently we provide packages for Ubuntu trusty 14.04 only.
    If you need to install mcloud on other OS, install it from source: :ref:`from_source`

.. note:: **NB!** Run installation commands as root user. (sudo su, or just login as root)

Add modera ubuntu repository::

    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 1B322208
    echo "deb http://ubuntu.dev.modera.org/debian trusty main" > /etc/apt/sources.list.d/modera.list

Install mcloud::

    apt-get update && apt-get install mcloud-full


Checking installation
=======================================

Just start mcloud shell::

    $ mcloud

    mcloud: ~@me>

Hit Ctrl+D to exit mcloud shell.