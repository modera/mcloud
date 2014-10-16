
.. _manual_install:

===================================
Manual installation
===================================

If you prefer to get more control how mcloud is installed, you can
install all parts of mcloud by yourself.

Prerequisites
============================

Install docker:
https://docs.docker.com/installation/

Make sure it's working::

    sudo docker run -i -t ubuntu echo -e "OK";


Mcloud installation
==========================

.. note::
    Currently we provide packages for Ubuntu trusty 14.04 only.
    If you need to install mcloud on other OS, install it from source: :ref:`from_source`


Add modera ubuntu repository::

    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 1B322208
    echo "deb http://ubuntu.dev.modera.org/debian trusty main" > /etc/apt/sources.list.d/modera.list

Add haproxy repository::

    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 1C61B9CD
    echo "deb http://ppa.launchpad.net/vbernat/haproxy-1.5/ubuntu trusty main" >> /etc/apt/sources.list.d/haproxy.list


Install mcloud::

    apt-get update && apt-get install mcloud


Installing required software
=======================================

redis-server
------------------------------

Install redis::

    sudo apt-get install redis-server


Install dnsmasq server
------------------------------

dnsmasq acts as dns proxy for local machine, we will configure it to proxify all request
to outer dns servers, except mcloud.lh subdomain.

Install dnamasq:

    sudo apt-get install dnsmasq

Replace content of /etc/dnsmasq.conf file with following 3 lines::

    interface=lo
    interface=docker0
    server=/mcloud.lh/172.17.42.1#7053

Replace '172.17.42.1' with your docker interface ip. You can get it using ifconfig command::

    $ ifconfig docker0

Start dnsmasq server::

    $ sudo service dnsmasq start


Checking installation
=======================================


Just start mcloud shell::

    $ mcloud

    mcloud: ~@me>

Hit Ctrl+D to exit mcloud shell.