mfcloud
======

mfcloud is a tool that orchestrates Docker containers localy and on
remote server.

Features:

- simple syntax mfcloud.yml, that describe containers you need for your application
- easily create application on remote deployment server
- easily push and pull volumes of Docker containers on remote server
- tcp balancer that knows which container serves which URL
- super-easy service discovery for applications

.. image:: docs/source/_static/mfcloud.png


Requirements
--------------

Linux (boot2docker will be supported a bit later)
Docker > 1.0.0
Redis server

Installation
-------------

Install docker: http://docs.docker.io/en/latest/installation/

Make sure you can run docker containers::

    sudo docker run -i -t ubuntu echo -e "OK";


Install packages::

    sudo apt-get install python-pip python-dev
    sudo pip install mfcloud

Run mfcloud server::

    sudo mflcoud-rpc-server

Test that mfcloud is working::

    $ mfcloud list

    +-----+---------+-------+
    | App | Version | State |
    +-----+---------+-------+
    +-----+---------+-------+
