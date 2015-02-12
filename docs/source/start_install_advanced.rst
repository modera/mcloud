
.. _manual_install:

===================================
Manual install
===================================

If you prefer to get more control on how ModeraCloud is installed, follow this guide to install all parts by yourself. Following this guideline is also recommended for public deployments.

Install Docker
============================

Follow `Docker website <https://docs.docker.com/installation/>`_ to get it installed.

Make sure it's working::

    sudo docker run -i -t ubuntu echo -e "Ok"

ModeraCloud installation
==========================

.. note::
    Currently we provide packages for Ubuntu trusty 14.04 only.
    If you need to install on any other version follow: :ref:`from_source`


Add Modera Ubuntu repository::

    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 1B322208
    echo "deb http://apt.mcloud.io/ trusty main" > /etc/apt/sources.list.d/modera.list

Add Haproxy repository::

    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 1C61B9CD
    echo "deb http://ppa.launchpad.net/vbernat/haproxy-1.5/ubuntu trusty main" >> /etc/apt/sources.list.d/haproxy.list
ModeraCloudall ModeraCloud::

    apt-get update && apt-get install mcloud haproxy


Installing required dependencies
=======================================

Redis server
------------------------------

Redis is used to cache the deployment configuration that is initially fed from the *mcloud.yml* files.

Install Redis::

    sudo apt-get install redis-server


Install Dnsmasq server
------------------------------

Dnsmasq acts as DNS proxy for local machine, we will configure it to proxify all requests
to outer DNS servers, except *mcloud.lh* subdomain.

Install Dnsmasq::

    sudo apt-get install dnsmasq

Replace content of */etc/dnsmasq.conf* file with following 3 lines::

    server=/mcloud.lh/127.0.0.1#7053

Start Dnsmasq server::

    $ sudo service dnsmasq start


Verify installation
=====================================

Start ModeraCloud shell::

    $ mcloud shell

    mcloud: ~@me>

Hit Ctrl+D to exit.
