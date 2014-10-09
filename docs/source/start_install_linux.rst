

===================================
Installation on linux
===================================

Instructions are given for Ubuntu linux, but except some details, like
package names and file-system paths, process is same on all operating systems.


Prerequisites
============================

Install docker:
https://docs.docker.com/installation/

Make sure it's working::

    sudo docker run -i -t ubuntu echo -e "OK";


Mfcloud installation
==========================

.. note::
    Currently we provide packages for Ubuntu trusty 14.04 only.
    If you need to install mfcloud on other OS, install it from source: :ref:`from_source`


Add modera ubuntu repository::

    sudo sudo sh -c 'wget -O - https://ubuntu.dev.modera.org/moderaci.gpg.key|apt-key add -'
    sudo sh -c 'echo "deb http://ubuntu.dev.modera.org/debian trusty main" > /etc/apt/sources.list.d/modera.list'
    sudo apt-get update

Install mfcloud::

    sudo apt-get install mfcloud


Installing required software
=======================================

redis-server
------------------------------

Install redis::

    sudo apt-get install redis-server


Install dnsmasq server
------------------------------

dnsmasq acts as dns proxy for local machine, we will configure it to proxify all request
to outer dns servers, except mfcloud.lh subdomain.

Install dnamasq:

    sudo apt-get install dnsmasq

Replace content of /etc/dnsmasq.conf file with following 3 lines::

    interface=lo
    interface=docker0
    server=/mfcloud.lh/172.17.42.1#7053

Replace '172.17.42.1' with your docker interface ip. You can get it using ifconfig command::

    $ ifconfig docker0

Start dnsmasq server::

    $ sudo service dnsmasq start


Checking installation
=======================================


Just start mfcloud shell::

    $ mfcloud

    mcloud: ~@me>

Hit Ctrl+D to exit mfcloud shell.