

===================================
Installation on linux
===================================

Instructions are given for Ubuntu linux, but except some details, like
package names and file-system paths, process is same on all operating systems.

What will be installed?
===========================

mfcloud-full package installs:

- mfcloud's binary files
- docker.io
- redis-server
- haproxy (NB! mfclouds overrides /haproxy on first start)
- dnsmasq (NB! mfclouds override /etc/dnsmasq.conf on post-install)

If you are not agree with this changes, you can install *mfcloud* package instead :ref:`manual_install`

Mfcloud installation
==========================

.. note::
    Currently we provide packages for Ubuntu trusty 14.04 only.
    If you need to install mfcloud on other OS, install it from source: :ref:`from_source`

Add modera ubuntu repository::

    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 1B322208
    echo "deb http://ubuntu.dev.modera.org/debian trusty main" > /etc/apt/sources.list.d/modera.list

Install mfcloud::

    apt-get update && apt-get install mfcloud-full


Checking installation
=======================================

Just start mfcloud shell::

    $ mfcloud

    mcloud: ~@me>

Hit Ctrl+D to exit mfcloud shell.